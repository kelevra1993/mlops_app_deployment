import subprocess
import sys
import os
from typing import List, Optional

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
    print(f"[*] Attempting to reserve {accelerator_type} on {machine_type} in {zone}...")
    
    command = [
        "gcloud", "compute", "reservations", "create", reservation_name,
        f"--machine-type={machine_type}",
        f"--accelerator=type={accelerator_type},count=1",
        f"--zone={zone}",
        "--vm-count=1",
        "--quiet"
    ]
    
    try:
        # We capture output to avoid spamming the console with expected errors during the search
        result = subprocess.run(command, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"[SUCCESS] Successfully reserved capacity in {zone}!")
            return True
        else:
            # If it failed, it usually means ZONE_RESOURCE_POOL_EXHAUSTED
            print(f"[FAILED] No capacity in {zone}.")
            return False
            
    except FileNotFoundError:
        print("Error: 'gcloud' CLI is not installed or not in PATH.")
        sys.exit(1)


def search_for_capacity(zones: List[str], reservation_name: str, machine_type: str, accelerator_type: str) -> Optional[str]:
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
    print(f"Starting capacity search across {len(zones)} zones...")
    
    for zone in zones:
        success = reserve_gpu(
            zone=zone,
            reservation_name=reservation_name,
            machine_type=machine_type,
            accelerator_type=accelerator_type
        )
        
        if success:
            print(f"\n>>> WINNER: Capacity found and reserved in {zone} <<<")
            return zone
            
    print("\n[!] Exhausted all provided zones. No capacity found.")
    return None


def main() -> None:
    """
    Orchestrates the GPU reservation process for the Triton Inference Server.
    It loops through preferred Google Cloud zones to find capacity for the required GPU,
    creates the reservation, and writes the terraform variables so the infrastructure deployment
    can proceed to provision the GKE cluster in the correct zone.
    """
    # Define the zones you want to search through in order of preference
    zones_to_search = [
        "europe-west1-b", 
        "europe-west1-c", 
        "europe-west1-d",
        "europe-west4-a",
        "europe-west4-b",
        "europe-west4-c",
        "europe-west3-a",
        "europe-west3-b",
        "europe-west3-c",
        "us-central1-a",
        "us-central1-b",
        "us-central1-c",
        "us-central1-f",
        "us-east1-b",
        "us-east1-c",
        "us-east1-d"
    ]
    
    reservation_name = "machine-learning-gpu-reservation"
    configurations = [
        {"machine_type": "g2-standard-4", "accelerator_type": "nvidia-l4"},
        {"machine_type": "n1-standard-4", "accelerator_type": "nvidia-tesla-t4"}
    ]
    
    successful_zone = None
    successful_machine = None
    successful_accelerator = None
    
    for config in configurations:
        print(f"\n=== Trying configuration: {config['machine_type']} with {config['accelerator_type']} ===")
        successful_zone = search_for_capacity(
            zones=zones_to_search,
            reservation_name=reservation_name,
            machine_type=config["machine_type"],
            accelerator_type=config["accelerator_type"]
        )
        if successful_zone:
            successful_machine = config["machine_type"]
            successful_accelerator = config["accelerator_type"]
            break
    
    if successful_zone:
        # Extract region from zone (e.g. europe-west1-b -> europe-west1)
        region = successful_zone.rsplit('-', 1)[0]
        
        # Determine the path to the terraform directory relative to this script
        script_directory = os.path.dirname(os.path.abspath(__file__))
        terraform_directory = os.path.join(script_directory, '..', '..', 'infrastructure', 'terraform')
        terraform_variables_path = os.path.join(terraform_directory, 'gpu.auto.tfvars')
        
        print(f"\nWriting Terraform variables to {terraform_variables_path}...")
        with open(terraform_variables_path, "w") as variables_file:
            variables_file.write(f'zone = "{successful_zone}"\n')
            variables_file.write(f'region = "{region}"\n')
            variables_file.write(f'reservation_name = "{reservation_name}"\n')
            variables_file.write(f'machine_type = "{successful_machine}"\n')
            variables_file.write(f'accelerator_type = "{successful_accelerator}"\n')
            
        print("Done! You can now run 'terraform apply' in the infrastructure/terraform directory.")
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
