import subprocess
import sys
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
    Main entry point for the script.
    """
    # Define the zones you want to search through in order of preference
    zones_to_search = [
        "europe-west4-b", 
        "europe-west4-c", 
        "europe-west3-a", 
        "europe-west3-b", 
        "europe-west3-c"
    ]
    
    reservation_name = "test-res"
    machine_type = "g2-standard-4"
    accelerator_type = "nvidia-l4"
    
    winner = search_for_capacity(
        zones=zones_to_search,
        reservation_name=reservation_name,
        machine_type=machine_type,
        accelerator_type=accelerator_type
    )
    
    if winner:
        # Example of what you could do next:
        # You could choose to immediately delete the test reservation if you just 
        # wanted to check availability before letting Terraform create it.
        # 
        # print(f"Deleting the temporary test reservation in {winner}...")
        # subprocess.run(["gcloud", "compute", "reservations", "delete", reservation_name, f"--zone={winner}", "--quiet"])
        pass
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
