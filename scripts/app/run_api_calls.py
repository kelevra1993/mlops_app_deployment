import os
import sys
import subprocess
import random
import glob
import requests
import threading
import multiprocessing
from typing import Optional, List, Tuple
import concurrent.futures
from tqdm import tqdm

project_root_directory = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(project_root_directory)

from app.utilities.os_utilities import get_command_path, print_green, print_red, print_blue


def get_api_url() -> Optional[str]:
    """
    Retrieves the external IP address of the deployed API service to construct the target URL.
    This function forms part of the MLOps pipeline load testing suite, allowing the script
    to automatically discover the active API endpoint without manual hardcoding.
    
    Returns:
        Optional[str]: The full URL to the '/infer' endpoint if successful, None otherwise.
    """
    kubectl_path = get_command_path(command_name="kubectl")
    if not kubectl_path:
        print_red(output="Error: kubectl command not found.")
        return None

    command = [kubectl_path, "get", "service", "api-service",
               "-o", "jsonpath='{.status.loadBalancer.ingress[0].ip}'"]

    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        ip_address = result.stdout.strip().replace("'", "")
        if ip_address:
            return f"http://{ip_address}:80/infer"
        else:
            print_red(output="External IP for api-service not yet provisioned.")
            return None
    except subprocess.CalledProcessError as e:
        print_red(output=f"Error retrieving API IP: {e}")
        return None


# Thread-local storage to hold one Session per thread, ensuring thread safety and reusing TCP connections
thread_local = threading.local()


def get_session() -> requests.Session:
    if not hasattr(thread_local, "session"):
        thread_local.session = requests.Session()
    return thread_local.session


def make_single_request(api_url: str, image_name: str, image_bytes: bytes) -> bool:
    """
    Helper function to execute a single API request from memory using a persistent TCP connection.
    
    Args:
        api_url (str): The endpoint URL.
        image_name (str): The filename of the image.
        image_bytes (bytes): The raw bytes of the image loaded from RAM.
        
    Returns:
        bool: True if the request was successful (HTTP 200), False otherwise.
    """
    session = get_session()
    try:
        files = {"image": (image_name, image_bytes, "image/png")}
        data = {"additional_comment": "Load Testing for Grafana (Extreme)"}

        response = session.post(api_url, files=files, data=data)
        return response.status_code == 200
    except Exception:
        return False


def worker_process_task(api_url: str, num_requests: int, loaded_images: List[Tuple[str, bytes]], num_threads: int) -> \
Tuple[int, int]:
    """
    Executes a chunk of requests in a separate Python process using an internal ThreadPoolExecutor.
    """
    successful = 0
    failed = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = []
        for _ in range(num_requests):
            img_name, img_bytes = random.choice(loaded_images)
            futures.append(executor.submit(make_single_request, api_url, img_name, img_bytes))

        for future in concurrent.futures.as_completed(futures):
            if future.result():
                successful += 1
            else:
                failed += 1

    return successful, failed


def run_inference_loops(api_url: str, num_iterations: int, number_processes: int = 0,
                        threads_per_process: int = 50) -> None:
    """
    Executes a continuous loop of POST requests to the API using multithreading to simulate high concurrent traffic.
    This function forms part of the MLOps pipeline load testing suite, designed to 
    stress-test the Triton Inference Server and generate rich utilization metrics in Grafana.
    
    Args:
        api_url (str): The complete URL of the inference endpoint to send requests to.
        num_iterations (int): The total number of requests to execute.
        number_processes (int): The number of CPU cores to utilize. 0 means use all available cores.
        threads_per_process (int): The number of concurrent threads per process.
    """
    data_directory = os.path.join(project_root_directory, "app", "data")
    image_paths = glob.glob(os.path.join(data_directory, "*.png"))

    if not image_paths:
        print_red(output="No images found in app/data/")
        return

    # Pre-load all images into RAM to eliminate disk I/O bottlenecks during the load test
    loaded_images = []
    for path in image_paths:
        with open(path, "rb") as f:
            loaded_images.append((os.path.basename(path), f.read()))

    if number_processes <= 0:
        number_processes = multiprocessing.cpu_count() or 4

    requests_per_process = num_iterations // number_processes
    remainder = num_iterations % number_processes

    print_blue(
        output=f"Spawning {number_processes} independent processes (with {threads_per_process} threads each) to execute {num_iterations} API calls...",
        add_separators=True)

    total_successful = 0
    total_failed = 0

    # We use ProcessPoolExecutor to bypass the GIL entirely and saturate the CPU
    with concurrent.futures.ProcessPoolExecutor(max_workers=number_processes) as executor:
        futures = []
        for i in range(number_processes):
            # Distribute remainder to the first process
            reqs = requests_per_process + (remainder if i == 0 else 0)
            if reqs > 0:
                futures.append(executor.submit(worker_process_task, api_url, reqs, loaded_images, threads_per_process))

        # Use tqdm to track progress as entire chunks/processes finish
        for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures),
                           desc="Processing Multicore Batches", unit="batch"):
            succ, fail = future.result()
            total_successful += succ
            total_failed += fail

    print_green(output=f"Load Test Complete! Success: {total_successful} | Failed: {total_failed}", add_separators=True)


def main() -> None:
    """
    Main entry point for testing the API and generating traffic for Grafana metrics.
    It retrieves the dynamic LoadBalancer IP and triggers the inference loop.
    """
    api_url = get_api_url()
    if api_url:
        run_inference_loops(api_url=api_url, num_iterations=10000, number_processes=0, threads_per_process=50)


if __name__ == "__main__":
    main()
