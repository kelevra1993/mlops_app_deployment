import sys
import os
import subprocess
import re
import argparse
from typing import Optional

# Ensure we can import from the app directory by adding the project root to sys.path
# Since the script is in scripts/infrastructure/docker, we need to go up 3 levels
project_root_directory = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.append(project_root_directory)

from app.utilities.constants import PROJECT_ID
from app.utilities.os_utilities import print_green, print_yellow, print_blue


def extract_region_from_terraform_variables(terraform_variables_file_path: str) -> str:
    """
    Extracts the GCP region from the Terraform variables file to dynamically configure Docker and Artifact Registry
    for the downstream MLOps application deployment pipeline.
    
    Args:
        terraform_variables_file_path (str): The absolute path to the gpu.auto.tfvars file containing the region.
        
    Returns:
        str: The extracted GCP region string.
    """
    extracted_region: Optional[str] = None
    try:
        with open(terraform_variables_file_path, 'r') as terraform_variables_file:
            for line_content in terraform_variables_file:
                region_regex_match = re.match(r'^region\s*=\s*"([^"]+)"', line_content.strip())
                if region_regex_match:
                    extracted_region = region_regex_match.group(1)
                    break
    except FileNotFoundError:
        print(f"❌ Error: Could not find the Terraform variables file at {terraform_variables_file_path}")
        sys.exit(1)

    if not extracted_region:
        print("❌ Error: Could not extract the region from the Terraform variables file.")
        sys.exit(1)

    return extracted_region


def main() -> None:
    """
    Automates the Docker build and push process for the Gradio frontend application within the MLOps pipeline.
    It fetches the active GCP region from Terraform, configures Docker authentication, and pushes the container 
    image to the correct Artifact Registry so it can be deployed by Kubernetes.
    
    Usage Example:
        python scripts/infrastructure/docker/build_and_push.py v4
    """
    argument_parser = argparse.ArgumentParser(description=(
        "Automate Docker build and push for MLOps pipeline.\n\n"
        "Example Of How To Run The Script:\n"
        "  - python scripts/infrastructure/docker/build_and_push.py v4\n"
        "  - python scripts/infrastructure/docker/build_and_push.py latest"
    ), formatter_class=argparse.RawTextHelpFormatter)
    argument_parser.add_argument("tag", help="The tag for the Docker image (e.g., v4, latest)")
    parsed_arguments = argument_parser.parse_args()

    terraform_variables_path = os.path.join(project_root_directory, 'infrastructure', 'terraform', 'gpu.auto.tfvars')

    # Get the gcp region which was decided based on the available gpus
    gcp_region = extract_region_from_terraform_variables(terraform_variables_file_path=terraform_variables_path)

    print_green("Successfully Retrieved Environment Variables", add_separators=True)
    print(f" ✅ Found Region: {gcp_region}")
    print(f" ✅ Found Project ID: {PROJECT_ID}")
    print(f" ✅ Using Tag: {parsed_arguments.tag}\n")

    # Get artifacts registry name as well as the image_name, it's tag and also the full docker image path.
    artifact_registry_name = "machine-learning-artifacts-registry"
    docker_image_name = f"gradio-app:{parsed_arguments.tag}"
    artifact_registry_domain = f"{gcp_region}-docker.pkg.dev"
    full_docker_image_path = f"{artifact_registry_domain}/{PROJECT_ID}/{artifact_registry_name}/{docker_image_name}"

    # Docker needs to have access to this artifact registry therefore some configuration is needed
    print(f"🔐 Configuring Docker authentication for {artifact_registry_domain}...")
    try:
        docker_configuration_command_list = ["gcloud", "auth", "configure-docker", artifact_registry_domain, "--quiet"]
        docker_configuration_command = " ".join(docker_configuration_command_list)
        print_yellow(f"Running Command : {docker_configuration_command}", add_separators=True)
        subprocess.run(docker_configuration_command_list, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print_green(f"Docker Configured Successfuly !!!", add_separators=True)
    except subprocess.CalledProcessError:
        print("❌ Error configuring Docker authentication")
        sys.exit(1)

    # Build and push the image while keeping in mind that the platfrom should be linux/amd64
    print(f"\n🚀 Building and pushing the Docker image...")
    print(f"📦 Image Path: {full_docker_image_path}")
    try:
        docker_build_and_push_command_list = [
            "docker", "buildx", "build",
            "--platform", "linux/amd64",
            "-f", "app/docker/Dockerfile",
            "-t", full_docker_image_path,
            "app/",
            "--push"]
        docker_build_and_push_command = " ".join(docker_build_and_push_command_list)
        print_yellow(f"Running Command : {docker_build_and_push_command}", add_separators=True)

        # subprocess.run(docker_build_and_push_command_list, cwd=project_root_directory, check=True)
        link_to_docker_image = (f"https://console.cloud.google.com/artifacts/docker/"
                                f"{PROJECT_ID}/{gcp_region}/{artifact_registry_name}?authuser=1&project={PROJECT_ID}")
        print_green(f"Image Pushed Successfully To : {link_to_docker_image} !!!", add_separators=True)
        print_blue(f"You Can Test The Image By Running : \n"
                   f" - docker run -it --rm {full_docker_image_path} /bin/bash")

    except subprocess.CalledProcessError:
        print("❌ Error building and pushing the Docker image")
        sys.exit(1)

    print("🎉 Successfully built and pushed the image!")


if __name__ == "__main__":
    main()
