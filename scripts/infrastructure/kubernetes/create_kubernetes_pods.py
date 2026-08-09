import sys
import os
import subprocess
import shutil
import time

from typing import List

from google.cloud import storage

# Ensure we can import from the app directory by adding the project root to sys.path
# Since the script is in scripts/infrastructure/kubernetes, we need to go up 3 levels
project_root_directory = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.append(project_root_directory)

from app.utilities.constants import PROJECT_ID
from app.utilities.os_utilities import (print_green, print_yellow, print_blue, get_command_path, print_red,
                                        extract_information_from_terraform_variables)
from app.utilities.gcp_utilities import upload_directory, get_kubernetes_cluster_credentials


def apply_kubernetes_manifest(manifest_file_path: str, region: str) -> None:
    """
    Applies a specific Kubernetes YAML manifest to the active cluster. 
    This function forms part of the MLOps pipeline to deploy application workloads 
    (like the frontend, API, or Triton Inference Server) programmatically.

    Args:
        manifest_file_path (str): The absolute or relative path to the Kubernetes YAML manifest file.
        region (str): The GCP region to inject into the manifest (e.g., replacing REGION_PLACEHOLDER).
    """
    print_blue(f"Applying Kubernetes configuration: {manifest_file_path}",
               add_separators=True, upper_space=True)

    kubectl_path = get_command_path(command_name="kubectl")
    if kubectl_path is None:
        print_red(output="❌ Error: kubectl command not found.", add_separators=True)
        sys.exit(1)

    # Replace REGION_PLACEHOLDER with the actual region
    with open(manifest_file_path, "r") as file:
        manifest_content = file.read()

    manifest_content = manifest_content.replace("REGION_PLACEHOLDER", region)

    temporary_manifest_path = manifest_file_path + ".temporary"
    with open(temporary_manifest_path, "w") as file:
        file.write(manifest_content)

    kubectl_apply_command_list = [kubectl_path, "apply", "-f", temporary_manifest_path]
    kubectl_apply_command_string = " ".join(kubectl_apply_command_list)

    print_yellow(f"Running Command : {kubectl_apply_command_string}")

    try:
        subprocess.run(kubectl_apply_command_list, check=True, cwd=project_root_directory)
        print_green(f"Successfully applied {os.path.basename(manifest_file_path)}!", add_separators=True)
    except subprocess.CalledProcessError:
        print_red(output=f"❌ Error applying Kubernetes manifest: {manifest_file_path}", add_separators=True)
        os.remove(temporary_manifest_path)
        sys.exit(1)

    os.remove(temporary_manifest_path)


def wait_and_print_gradio_service_ip() -> None:
    """
    Waits for the Gradio service to be assigned an external IP address and prints it.
    
    This function forms part of the MLOps pipeline deployment to provide the user 
    with a direct, clickable link to access the Gradio frontend once it is live.
    """
    print_blue("Waiting for the Gradio service to get an external IP... (this may take a few minutes)",
               add_separators=True, upper_space=1)

    kubectl_path = get_command_path(command_name="kubectl")
    if not kubectl_path:
        print_red("❌ Error: kubectl command not found.")
        return

    command = [kubectl_path, "get", "service", "gradio-service",
               "-o", "jsonpath='{.status.loadBalancer.ingress[0].ip}'"]
    print(f"Running : {' '.join(command)}")
    max_attempts = 60
    for _ in range(max_attempts):
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            ip_address = result.stdout.strip().replace("'", '')
            if ip_address:
                app_url = f"http://{ip_address}:80"
                print_green(f"🎉 Gradio App is live and accessible at: {app_url}",
                            add_separators=True, upper_space=1,
                            lower_space=1)
                return
        except subprocess.CalledProcessError:
            pass

        time.sleep(5)

    print_yellow(
        "⚠️ Timed out waiting for external IP. You can check manually with: kubectl get service gradio-service",
        add_separators=True, upper_space=1)


def main() -> None:
    """
    Automates the Kubernetes deployment process for the MLOps pipeline.
    It sequentially applies the core application manifests (API, Gradio Frontend, and Triton Backend) 
    to spin up the necessary pods and services in the Google Kubernetes Engine (GKE) cluster.
    """
    print_green("Starting Kubernetes Pod Creation Automation", add_separators=True, lower_space=1)

    terraform_variables_path = os.path.join(project_root_directory, 'infrastructure', 'terraform',
                                            'location.auto.tfvars')
    terraform_info = extract_information_from_terraform_variables(
        terraform_variables_file_path=terraform_variables_path)
    gcp_region = terraform_info.get("region")
    gcp_zone = terraform_info.get("zone")

    if not gcp_region or not gcp_zone:
        print_red(output="❌ Error: Region or Zone not found in Terraform variables.", add_separators=True)
        sys.exit(1)

    print_blue("Fetching Kubernetes credentials before proceeding...", add_separators=True)
    get_kubernetes_cluster_credentials(cluster_name="machine-learning-cluster", zone=gcp_zone, project_id=PROJECT_ID)

    print_blue("Uploading models to GCS bucket before applying manifests...",
               add_separators=True, upper_space=1)
    storage_client = storage.Client(project=PROJECT_ID)
    bucket_name = "machine-learning-ops-images-bucket-2026"
    destination_prefix = "served_models"
    local_models_directory = os.path.join(project_root_directory, "infrastructure/docker/triton/served_models")

    upload_directory(storage_client=storage_client, bucket_name=bucket_name,
                     local_directory_path=local_models_directory,
                     destination_prefix=destination_prefix,
                     verbose=False)

    link_to_served_models = f"https://console.cloud.google.com/storage/browser/{bucket_name}/{destination_prefix}"
    print_green(f"Successfully uploaded models to GCS At {link_to_served_models} !", add_separators=True)

    # Define the core application manifests that need to be deployed
    kubernetes_manifest_paths: List[str] = ["infrastructure/kubernetes/applications/triton.yaml",
                                            "infrastructure/kubernetes/applications/api.yaml",
                                            "infrastructure/kubernetes/applications/gradio.yaml"]

    print_blue(f"To Watch the pods as they transition from 'Pending' to 'Running' : \n"
               f" - kubectl get pods -l app=gradio --watch", upper_space=1)

    for manifest_path in kubernetes_manifest_paths:
        absolute_manifest_path = os.path.join(project_root_directory, manifest_path)

        # Verify the file exists before attempting to apply it
        if not os.path.exists(absolute_manifest_path):
            print_red(output=f"❌ Error: Kubernetes manifest not found at {absolute_manifest_path}", add_separators=True)
            sys.exit(1)

        apply_kubernetes_manifest(manifest_file_path=absolute_manifest_path, region=gcp_region)

    print("\n--- Kubernetes pods and services are currently being deployed! ---\n")

    wait_and_print_gradio_service_ip()


if __name__ == "__main__":
    main()
