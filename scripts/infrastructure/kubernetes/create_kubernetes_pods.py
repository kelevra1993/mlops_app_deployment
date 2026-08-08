import sys
import os
import subprocess
import shutil

from typing import List

from google.cloud import storage

# Ensure we can import from the app directory by adding the project root to sys.path
# Since the script is in scripts/infrastructure/kubernetes, we need to go up 3 levels
project_root_directory = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.append(project_root_directory)

from app.utilities.constants import PROJECT_ID
from app.utilities.os_utilities import (print_green, print_yellow, print_blue, get_command_path, print_red,
                                        extract_region_from_terraform_variables)
from app.utilities.gcp_utilities import upload_directory


def apply_kubernetes_manifest(manifest_file_path: str, region: str) -> None:
    """
    Applies a specific Kubernetes YAML manifest to the active cluster. 
    This function forms part of the MLOps pipeline to deploy application workloads 
    (like the frontend, API, or Triton Inference Server) programmatically.
    
    Args:
        manifest_file_path (str): The absolute or relative path to the Kubernetes YAML manifest file.
        region (str): The GCP region to inject into the manifest (e.g., replacing REGION_PLACEHOLDER).
    """
    print_blue(f"Applying Kubernetes configuration: {manifest_file_path}", add_separators=True)

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


def main() -> None:
    """
    Automates the Kubernetes deployment process for the MLOps pipeline.
    It sequentially applies the core application manifests (API, Gradio Frontend, and Triton Backend) 
    to spin up the necessary pods and services in the Google Kubernetes Engine (GKE) cluster.
    """
    print_green("Starting Kubernetes Pod Creation Automation", add_separators=True)

    terraform_variables_path = os.path.join(project_root_directory, 'infrastructure', 'terraform',
                                            'location.auto.tfvars')
    gcp_region = extract_region_from_terraform_variables(terraform_variables_file_path=terraform_variables_path)

    print_blue("Uploading models to GCS bucket before applying manifests...", add_separators=True)
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

    print_blue(f"\nTo Watch the pods as they transition from 'Pending' to 'Running' : \n"
               f" - kubectl get pods -l app=gradio --watch")

    for manifest_path in kubernetes_manifest_paths:
        absolute_manifest_path = os.path.join(project_root_directory, manifest_path)

        # Verify the file exists before attempting to apply it
        if not os.path.exists(absolute_manifest_path):
            print_red(output=f"❌ Error: Kubernetes manifest not found at {absolute_manifest_path}", add_separators=True)
            sys.exit(1)

        apply_kubernetes_manifest(manifest_file_path=absolute_manifest_path, region=gcp_region)

    print_green("\n🎉 All Kubernetes pods and services have been successfully deployed!\n", add_separators=True)


if __name__ == "__main__":
    main()
