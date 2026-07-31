import os
from google.cloud import storage

# Initialize the Google Cloud Storage client. Like BigQuery, this will use 
# the default credentials available in the environment.
client = storage.Client(project="ml-ops-classifier-app")

BUCKET_NAME = "machine-learning-ops-images-bucket-2026"
PREFIX = "inferred_image"

def upload_inferred_image(local_file_path: str, destination_blob_name: str) -> str:
    """
    Uploads an image from the local filesystem to the GCS bucket under the 'inferred_image' prefix.
    
    Args:
        local_file_path (str): The absolute path to the local image file.
        destination_blob_name (str): The name to give the file in GCS (e.g. uuid.jpg).
        
    Returns:
        str: The full gs:// URI of the uploaded object, or an empty string if upload fails.
    """
    try:
        bucket = client.bucket(BUCKET_NAME)
        
        # The blob path is the combination of our prefix and the desired filename
        full_blob_path = f"{PREFIX}/{destination_blob_name}"
        
        blob = bucket.blob(full_blob_path)
        
        # Perform the actual upload from the local file
        blob.upload_from_filename(local_file_path)
        
        gcs_uri = f"gs://{BUCKET_NAME}/{full_blob_path}"
        print(f"Successfully uploaded image to {gcs_uri}")
        
        return gcs_uri
    except Exception as e:
        print(f"Error uploading image to GCS: {e}")
        return ""
