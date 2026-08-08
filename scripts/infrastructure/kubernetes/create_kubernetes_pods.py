import sys
import os
import subprocess
import shutil

from typing import List

# Ensure we can import from the app directory by adding the project root to sys.path
# Since the script is in scripts/infrastructure/kubernetes, we need to go up 3 levels
project_root_directory = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.append(project_root_directory)

from app.utilities.os_utilities import print_green, print_yellow, print_blue, get_command_path, print_red


def apply_kubernetes_manifest(manifest_file_path: str) -> None:
    """
    Applies a specific Kubernetes YAML manifest to the active cluster. 
    This function forms part of the MLOps pipeline to deploy application workloads 
    (like the frontend, API, or Triton Inference Server) programmatically.
    
    Args:
        manifest_file_path (str): The absolute or relative path to the Kubernetes YAML manifest file.
    """
    print_blue(f"Applying Kubernetes configuration: {manifest_file_path}", add_separators=True)

    kubectl_path = get_command_path(command_name="kubectl")
    if kubectl_path is None:
        print_red(output="❌ Error: kubectl command not found.", add_separators=True)
        sys.exit(1)

    kubectl_apply_command_list = [kubectl_path, "apply", "-f", manifest_file_path]
    kubectl_apply_command_string = " ".join(kubectl_apply_command_list)

    print_yellow(f"Running Command : {kubectl_apply_command_string}")

    try:
        subprocess.run(kubectl_apply_command_list, check=True, cwd=project_root_directory)
        print_green(f"Successfully applied {os.path.basename(manifest_file_path)}!", add_separators=True)
    except subprocess.CalledProcessError:
        print(f"❌ Error applying Kubernetes manifest: {manifest_file_path}")
        sys.exit(1)


def main() -> None:
    """
    Automates the Kubernetes deployment process for the MLOps pipeline.
    It sequentially applies the core application manifests (API, Gradio Frontend, and Triton Backend) 
    to spin up the necessary pods and services in the Google Kubernetes Engine (GKE) cluster.
    """
    print_green("Starting Kubernetes Pod Creation Automation", add_separators=True)

    from app.utilities.gcp_utilities import upload_directory
    from google.cloud import storage

    print_blue("Uploading models to GCS bucket before applying manifests...", add_separators=True)
    storage_client = storage.Client()
    bucket_name = "machine-learning-ops-images-bucket-2026"
    local_models_directory = os.path.join(project_root_directory, "infrastructure/docker/triton/served_models")
    
    upload_directory(
        storage_client=storage_client,
        bucket_name=bucket_name,
        local_directory_path=local_models_directory,
        destination_prefix="served_models"
    )
    print_green("Successfully uploaded models to GCS!", add_separators=True)

    # Define the core application manifests that need to be deployed
    kubernetes_manifest_paths: List[str] = [
        "infrastructure/kubernetes/applications/triton.yaml",
        "infrastructure/kubernetes/applications/api.yaml",
        "infrastructure/kubernetes/applications/gradio.yaml"]

    for manifest_path in kubernetes_manifest_paths:
        print("")
        absolute_manifest_path = os.path.join(project_root_directory, manifest_path)

        # Verify the file exists before attempting to apply it
        if not os.path.exists(absolute_manifest_path):
            print(f"❌ Error: Kubernetes manifest not found at {absolute_manifest_path}")
            sys.exit(1)

        apply_kubernetes_manifest(manifest_file_path=manifest_path)

    print("\n🎉 All Kubernetes pods and services have been successfully deployed!\n")


if __name__ == "__main__":
    main()
