import subprocess
import sys
import os
from typing import List, Optional

project_root_directory = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.append(project_root_directory)

from app.utilities.constants import ZONES_TO_SEARCH, GPU_CONFIGURATIONS, PROJECT_ID
from app.utilities.gcp_utilities import check_existing_reservation
from app.utilities.os_utilities import get_command_path, print_blue, print_green, print_yellow, print_red


def reserve_gpu(zone: str, reservation_name: str, machine_type: str, accelerator_type: str) -> bool:
    """
    Attempts to create a single GPU reservation in the specified zone.
    
    Args:
        zone: The GCP zone (e.g., 'europe-west3-a').
        reservation_name: The name of the reservation to create.
        machine_type: The GCP machine type (e.g., 'g2-standard-4').
        accelerator_type: The accelerator type (e.g., 'nvidia-l4').
        
    Returns:
        True if the reservation was successfully created, False otherwise.
    """

    # First try to see if we already have a reservation of a gpu in place, if so no need to try to reserve one.
    print_blue(f"[*] Attempting to reserve {accelerator_type} on {machine_type} in {zone}...")

    gcloud_path = get_command_path(command_name="gcloud")
    if not gcloud_path:
        print_red("❌ Error: gcloud command not found.", add_separators=True)
        sys.exit(1)

    command = [
        gcloud_path, "compute", "reservations", "create", reservation_name,
        f"--project={PROJECT_ID}",
        f"--machine-type={machine_type}",
        f"--accelerator=type={accelerator_type},count=1",
        f"--zone={zone}",
        "--vm-count=1",
        "--require-specific-reservation",
        "--quiet"]

    try:
        # We capture output to avoid spamming the console with expected errors during the search
        result = subprocess.run(command, capture_output=True, text=True)

        if result.returncode == 0:
            print_green(f"[SUCCESS] Successfully reserved capacity in {zone}!", add_separators=True)
            return True
        else:
            # If it failed, it usually means ZONE_RESOURCE_POOL_EXHAUSTED
            print_yellow(f"[FAILED] No capacity in {zone}.")
            return False

    except FileNotFoundError:
        print_red("Error: 'gcloud' CLI is not installed or not in PATH.", add_separators=True)
        sys.exit(1)


def search_for_capacity(zones: List[str], reservation_name: str,
                        machine_type: str, accelerator_type: str) -> Optional[str]:
    """
    Iterates through a list of zones and attempts to reserve capacity until successful.
    Args:
        zones: A list of GCP zones to search through.
        reservation_name: The name of the reservation to create.
        machine_type: The GCP machine type (e.g., 'g2-standard-4').
        accelerator_type: The accelerator type (e.g., 'nvidia-l4').
        
    Returns:
        The name of the zone where the reservation was successful, or None if all failed.
    """
    print_blue(f"Starting capacity search across {len(zones)} zones...", add_separators=True)

    for zone in zones:
        success = reserve_gpu(zone=zone, reservation_name=reservation_name,
                              machine_type=machine_type, accelerator_type=accelerator_type)
        if success:
            print_green(f">>> WINNER: Capacity found and reserved in {zone} <<<", add_separators=True)
            return zone

    print_red("[!] Exhausted all provided zones. No capacity found.", add_separators=True)
    return None


def create_terraform_location_variables(successful_zone: str, successful_machine: str,
                                        successful_accelerator: str, reservation_name: str) -> None:
    """
    Generates the Terraform variables file (location.auto.tfvars) to configure the deployment location.
    
    This function forms part of the MLOps pipeline to ensure that the infrastructure (like the GKE cluster)
    is provisioned in the exact same region and zone where the required GPU capacity was successfully reserved.
    
    Args:
        successful_zone (str): The GCP zone where capacity was found (e.g., 'europe-west3-a').
        successful_machine (str): The GCP machine type reserved (e.g., 'g2-standard-4').
        successful_accelerator (str): The accelerator type reserved (e.g., 'nvidia-l4').
        reservation_name (str): The name of the created reservation.
    """
    # Extract region from zone (e.g. europe-west1-b -> europe-west1)
    region = successful_zone.rsplit('-', 1)[0]

    # Determine the path to the terraform directory relative to this script
    script_directory = os.path.dirname(os.path.abspath(__file__))
    terraform_directory = os.path.join(script_directory, '..', '..', '..', 'infrastructure', 'terraform')
    terraform_variables_path = os.path.join(terraform_directory, 'location.auto.tfvars')

    print_blue(f"Writing Terraform variables to {terraform_variables_path}...", add_separators=True)
    with open(terraform_variables_path, "w") as variables_file:
        variables_file.write(
            '# This file is automatically generated by reserve_gpu_and_setup_infrastructure_location.py.\n')
        variables_file.write(
            '# It sets the region and zone dynamically based on where the GPU was successfully reserved.\n')
        variables_file.write(f'zone = "{successful_zone}"\n')
        variables_file.write(f'region = "{region}"\n')
        variables_file.write(f'reservation_name = "{reservation_name}"\n')
        variables_file.write(f'machine_type = "{successful_machine}"\n')
        variables_file.write(f'accelerator_type = "{successful_accelerator}"\n')

    print_green("Done! You can now run 'terraform apply' in the infrastructure/terraform directory.",
                add_separators=True)


def main() -> None:
    """
    Orchestrates the GPU reservation process for the Triton Inference Server.
    It loops through preferred Google Cloud zones to find capacity for the required GPU,
    creates the reservation, and writes the terraform variables so the infrastructure deployment
    can proceed to provision the GKE cluster in the correct zone.
    """
    reservation_name = "machine-learning-gpu-reservation"

    print_blue(f"[*] Checking for existing reservation '{reservation_name}'...", add_separators=True)
    existing_reservation = check_existing_reservation(reservation_name=reservation_name, project_id=PROJECT_ID)

    if existing_reservation:
        successful_zone, successful_machine, successful_accelerator = existing_reservation
        print_green(f">>> FOUND EXISTING RESERVATION <<<", add_separators=True)
        print_green(f"Zone: {successful_zone}\nMachine: {successful_machine}\nAccelerator: {successful_accelerator}")
    else:
        successful_zone = None
        successful_machine = None
        successful_accelerator = None

        for config in GPU_CONFIGURATIONS:
            print_yellow(f"=== Trying configuration: "
                         f"{config['machine_type']} with {config['accelerator_type']} ===", add_separators=True)
            successful_zone = search_for_capacity(zones=ZONES_TO_SEARCH,
                                                  reservation_name=reservation_name,
                                                  machine_type=config["machine_type"],
                                                  accelerator_type=config["accelerator_type"])

            # Since we found a successful zone now we set the default location to it.
            if successful_zone:
                successful_machine = config["machine_type"]
                successful_accelerator = config["accelerator_type"]
                break

    if successful_zone and successful_machine and successful_accelerator:
        create_terraform_location_variables(successful_zone=successful_zone,
                                            successful_machine=successful_machine,
                                            successful_accelerator=successful_accelerator,
                                            reservation_name=reservation_name)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
