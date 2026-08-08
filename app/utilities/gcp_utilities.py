import os
import subprocess
import json
import warnings
from typing import List, Dict, Optional, Tuple
from google.cloud import bigquery
from google.cloud import storage
from datetime import datetime
from app.utilities.os_utilities import get_command_path

# Suppress Google Auth UserWarnings regarding Application Default Credentials and Quota Projects
warnings.filterwarnings("ignore", "Your application has authenticated using end user credentials")


def upload_object(storage_client: storage.Client, bucket_name: str, local_file_path: str,
                  destination_file_name: str) -> str:
    """
    Uploads a processed image to Google Cloud Storage.

    This function is a critical step in the MLOps pipeline. It takes an image
    and uploads it to the provided GCS bucket. By storing these objects in GCS, 
    downstream analytics and the BigQuery history table can reference the exact 
    images the model inferred on.

    Args:
        storage_client (storage.Client): The Google Cloud Storage client used for authentication and connection.
        bucket_name (str): The name of the target GCS bucket where the object should be stored.
        local_file_path (str): The absolute or relative path to the local file to be uploaded.
        destination_file_name (str): The full path and filename the object will have in the GCS bucket.

    Returns:
        str: The full GCS URI (gs://bucket/path) of the successfully uploaded object, or an empty string if it fails.
    """
    try:
        # Create bucket object
        bucket = storage_client.bucket(bucket_name)

        # Create blob object
        blob = bucket.blob(destination_file_name)

        # Perform the actual upload from the local file
        blob.upload_from_filename(local_file_path)

        gcs_uri = f"gs://{bucket_name}/{destination_file_name}"
        print(f"Successfully uploaded object to {gcs_uri}")

        return gcs_uri
    except Exception as e:
        print(f"Error uploading object to GCS: {e}")
        return ""


def insert_inference_data_in_bigquery(bigquery_client: bigquery.Client, table_reference: str, uuid_str: str,
                                      predicted_class: str, probability: float, kubernetes_node: str,
                                      gcs_image_uri: str, additional_comment: str) -> None:
    """
    Inserts a single inference record into the BigQuery inference_history table. 
    This acts as the central data warehouse component of the MLOps pipeline, allowing for 
    downstream data analytics, model monitoring, and drift detection over time.

    Args:
        bigquery_client (bigquery.Client): The BigQuery client used for executing the insert job.
        table_reference (str): The BigQuery table reference to insert data into (e.g., project.dataset.table).
        uuid_str (str): A unique identifier for the inference run.
        predicted_class (str): The class predicted by the model (e.g. 'circles' or 'squares').
        probability (float): The confidence score of the prediction.
        kubernetes_node (str): The name of the node/replica processing this request.
        gcs_image_uri (str): The Google Cloud Storage URI where the inferred image was saved.
        additional_comment (str): Any extra comments to store alongside the record.
        
    Returns:
        None
    """

    # We construct the row dictionary matching the schema defined in Terraform.
    # The timestamp is generated right here before insertion.
    row_to_insert = {
        "uuid": uuid_str,
        "predicted_class": predicted_class,
        "probability": float(probability),
        "timestamp": datetime.utcnow().isoformat(),
        "kubernetes_node": kubernetes_node,
        "gcs_image_uri": gcs_image_uri,
        "additional_comment": additional_comment
    }

    # insert_rows_json streams data directly into BigQuery.
    errors = bigquery_client.insert_rows_json(table_reference, [row_to_insert])

    if errors:
        print(f"Encountered errors while inserting rows into BigQuery: {errors}")
    else:
        print(f"Successfully inserted inference record {uuid_str} into BigQuery.")


def get_recent_inferences(bigquery_client: bigquery.Client, table_reference: str,
                          target_columns: List[str], limit: int = 5) -> List[Dict]:
    """
    Retrieves the most recent inference records from BigQuery.
    
    This function provides a mechanism for the Gradio frontend to query and display 
    the latest inference histories and model predictions to end users in real-time.

    Args:
        bigquery_client (bigquery.Client): The BigQuery client used to execute the query.
        table_reference (str): The BigQuery table reference to query (e.g., project.dataset.table).
        target_columns (List[str]): A list of column names to retrieve from the BigQuery table.
        limit (int): The maximum number of records to retrieve. Default is 5.

    Returns:
        List[Dict]: A list of dictionary objects representing the rows.
    """
    # We use a SQL query to fetch the latest rows by ordering the timestamp descending.
    query = f"""
        SELECT 
            {', '.join(target_columns)}
        FROM 
            `{table_reference}`
        ORDER BY 
            timestamp DESC
        LIMIT {limit}
    """

    try:
        query_job = bigquery_client.query(query)
        results = query_job.result()  # Wait for the job to complete

        # Convert the BigQuery Row objects to standard python dictionaries
        rows = [dict(row) for row in results]
        return rows
    except Exception as e:
        print(f"Error retrieving recent inferences from BigQuery: {e}")
        return []


def check_existing_reservation(reservation_name: str, project_id: str) -> Optional[Tuple[str, str, str]]:
    """
    Checks if a GCP capacity reservation with the given name already exists across all zones.
    
    This function forms part of the MLOps pipeline to ensure we don't unnecessarily
    re-create reservations or search for capacity if a valid reservation is already
    active and available for the infrastructure deployment.
    
    Args:
        reservation_name (str): The name of the reservation to search for.
        project_id (str): The GCP project ID to run the command against.
        
    Returns:
        Optional[Tuple[str, str, str]]: A tuple containing (zone, machine_type, accelerator_type) 
        if the reservation exists, otherwise None.
    """
    try:
        gcloud_path = get_command_path(command_name="gcloud")
        if not gcloud_path:
            print("❌ Error: gcloud command not found.")
            return None

        # We list all reservations and format the output as JSON for easy parsing.
        command = [
            gcloud_path, "compute", "reservations", "list",
            f"--project={project_id}",
            f"--filter=name={reservation_name}",
            "--format=json"]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        reservations = json.loads(result.stdout)

        if reservations and len(reservations) > 0:
            reservation = reservations[0]
            # Zone is returned as a full URL,
            # e.g., https://www.googleapis.com/compute/v1/projects/project/zones/europe-west3-a
            zone = reservation.get("zone", "").split("/")[-1]
            specific_reservation = reservation.get("specificReservation", {})
            instance_properties = specific_reservation.get("instanceProperties", {})

            machine_type = instance_properties.get("machineType", "")

            # Accelerators are in a list, we just grab the first one assuming 1 accelerator
            guest_accelerators = instance_properties.get("guestAccelerators", [])
            accelerator_type = ""
            if guest_accelerators:
                accelerator_type = guest_accelerators[0].get("acceleratorType", "")

            if zone and machine_type and accelerator_type:
                return (zone, machine_type, accelerator_type)

    except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError) as e:
        print(f"Error checking existing reservation: {e}")

    return None


def upload_directory(storage_client: storage.Client, bucket_name: str,
                     local_directory_path: str, destination_prefix: str, verbose: bool = False) -> None:
    """
    Uploads an entire local directory to Google Cloud Storage.

    This function supports the MLOps pipeline by ensuring that model artifacts 
    are securely and accurately copied from the local repository to the target 
    GCS bucket, allowing the Triton Inference Server to dynamically load them.

    Args:
        storage_client (storage.Client): The Google Cloud Storage client used for connection.
        bucket_name (str): The name of the GCS bucket where the models will be stored.
        local_directory_path (str): The absolute or relative path to the local directory containing models.
        destination_prefix (str): The prefix (folder path) in the GCS bucket where models are placed.

    Returns:
        None
    """
    bucket = storage_client.bucket(bucket_name)

    for root, _, files in os.walk(local_directory_path):
        for file in files:
            local_file_path = os.path.join(root, file)

            # Calculate the relative path from the local directory
            relative_path = os.path.relpath(local_file_path, local_directory_path)

            # Ensure correct path separator for GCS
            destination_file_name = os.path.join(destination_prefix, relative_path).replace("\\", "/")

            blob = bucket.blob(destination_file_name)
            try:
                blob.upload_from_filename(local_file_path)
                if verbose:
                    print(f"Successfully uploaded {local_file_path} to gs://{bucket_name}/{destination_file_name}")
            except Exception as e:
                print(f"Error uploading {local_file_path} to GCS: {e}")
