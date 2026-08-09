import cv2
import os
import sys
import uuid
from typing import Tuple, List, Any

# Ensure the root project directory is in the Python path for imports to work correctly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app.utilities.inference_utilities import get_images, perform_inference
from app.utilities.gcp_utilities import insert_inference_data_in_bigquery, get_recent_inferences, upload_object
from app.utilities.os_utilities import print_green, print_blue, print_red, print_yellow, print_dictionary


def get_default_inference_data_images(data_directory: str) -> List[str]:
    """
    Retrieves default images from the specified directory to populate the Gradio frontend selection dropdown,
     allowing users to test the Triton inference backend without uploading their own images.
    
    Args:
        data_directory (str): The local directory path containing default images for inference testing.
        
    Returns:
        List[str]: A list of file paths for the images found in the directory.
    """

    if os.path.exists(data_directory):
        return get_images(path=data_directory, basename=False)

    return []


def determine_image_to_process(user_image_path: str, default_image_name: str,
                               default_data_directory: str) -> Tuple[str, str, Any]:
    """
    Determines which image to process for inference within the Gradio frontend based on user input.
    
    This function acts as a preprocessing step in the MLOps pipeline, giving precedence to user-uploaded 
    images. If no user image is provided, it falls back to a default test image to ensure the Triton 
    inference backend always receives a valid OpenCV image array.
    
    Args:
        user_image_path (str): The file path of the uploaded image.
        default_image_name (str): The filename of the default selected image.
        default_data_directory (str): The directory containing the default images.
        
    Returns:
        Tuple[str, str, Any]: A tuple containing the resolved image name, image path, and the OpenCV image array to process.
    """
    image_name = "Unknown"
    image_path = None

    if user_image_path is not None:
        # If user uploaded an image, it takes precedence
        image_name = os.path.basename(user_image_path)
        image_path = user_image_path

    elif default_image_name is not None:
        # Otherwise, use the selected inference data image
        default_image_path = os.path.join(default_data_directory, default_image_name)
        image_name = default_image_name
        image_path = default_image_path

    image_to_process = cv2.imread(image_path)

    return image_name, image_path, image_to_process


def upload_data_to_google_cloud(image_name: str, image_path: str, predicted_class: str, score: float,
                                additional_comment: str, destination_file_prefix: str, bucket_name: str,
                                table_reference: str, bigquery_client: Any, storage_client: Any) -> None:
    """
    Uploads the image to Google Cloud Storage and inserts inference metadata into BigQuery.
    
    This function handles generating a unique UUID for the inference run, uploading the image
    to the configured GCS bucket, and recording the inference results in BigQuery for downstream analytics.
    
    Args:
        image_name (str): The name of the image file.
        image_path (str): The local file path to the image.
        predicted_class (str): The class predicted by the model.
        score (float): The confidence probability score of the prediction.
        additional_comment (str): Any additional comments provided by the userow.
        destination_file_prefix (str): The prefix (folder) in GCS for the blob name.
        bucket_name (str): The name of the GCS bucket.
        table_reference (str): The BigQuery table reference.
        bigquery_client (Any): The BigQuery client object.
        storage_client (Any): The Google Cloud Storage client object.
    
    Returns:
        None
    """
    # Generate UUID for this inference run
    inference_uuid = str(uuid.uuid4())

    # Upload to Google Cloud Storage
    gcs_blob_name = f"{destination_file_prefix}/{inference_uuid}_{image_name}"
    gcs_uri = upload_object(storage_client=storage_client,
                            bucket_name=bucket_name,
                            local_file_path=image_path,
                            destination_file_name=gcs_blob_name)

    # Save to BigQuery with the required prefix
    prefixed_comment = f"Called By Gradio : {additional_comment}" if additional_comment else "Called By Gradio : "
    replica_name = os.getenv("REPLICA_NAME", "POD NOT IDENTIFIED")

    insert_inference_data_in_bigquery(
        bigquery_client=bigquery_client, table_reference=table_reference,
        uuid_str=inference_uuid, predicted_class=predicted_class, probability=score,
        kubernetes_node=replica_name, gcs_image_uri=gcs_uri, additional_comment=prefixed_comment)


def process_image(user_image_path: str, default_image_name: str, additional_comment: str, default_data_directory: str,
                  client: Any, inferred_images_prefix: str, bucket_name: str, table_reference: str,
                  bigquery_client: Any, storage_client: Any) -> Tuple[str, float, str, str]:
    """
    Acts as the main handler for the Gradio frontend, orchestrating the end-to-end inference request.
    
    This function coordinates the MLOps pipeline for a single user request by selecting the appropriate image, 
    running model inference via the Triton backend, and storing the prediction results in Google Cloud Storage 
    and BigQuery for downstream analytics and monitoring.
    
    Args:
        user_image_path (str): Filepath to the user-uploaded image.
        default_image_name (str): The filename of the selected default test image.
        additional_comment (str): The user's input from the comment Textbox.
        default_data_directory (str): The directory containing the default test images.
        client (Any): The Triton Inference Server client object.
        inferred_images_prefix (str): Prefix (folder) in GCS for the uploaded image blob.
        bucket_name (str): The GCS bucket name for storing the image.
        table_reference (str): The BigQuery table reference for storing inference metadata.
        bigquery_client (Any): The BigQuery client object.
        storage_client (Any): The Google Cloud Storage client object.
        
    Returns:
        Tuple[str, float, str, str]: A tuple containing the :
         image name, confidence score, predicted class, and local image path.
    """
    image_name, image_path, image_to_process = determine_image_to_process(
        user_image_path=user_image_path,
        default_image_name=default_image_name,
        default_data_directory=default_data_directory)

    if image_to_process is None:
        return image_name, 0.0, "Failed to load image", None

    # Run inference
    print_blue(f"Running Inference On {image_name}",upper_space=1)
    predicted_class, score = perform_inference(image=image_to_process,
                                               client=client,
                                               input_tensor='Input-Producer/Placeholders/Images/Placeholder_1:0',
                                               output_tensor='Outputs/Softmax:0',
                                               height=300, width=300, keep_ratio=True, center=False)
    print_green(f"Inference Ran On {image_name} Completed !!!")

    # Upload data to bigquery and google cloud storage.
    upload_data_to_google_cloud(image_name=image_name, image_path=image_path,
                                predicted_class=predicted_class, score=score, additional_comment=additional_comment,
                                destination_file_prefix=inferred_images_prefix, bucket_name=bucket_name,
                                table_reference=table_reference, bigquery_client=bigquery_client,
                                storage_client=storage_client)

    return image_name, score, predicted_class, image_path


def fetch_recent_inferences(target_columns: List[str], bigquery_client: Any, table_reference: str) -> List[List[Any]]:
    """
    Fetches the 5 most recent inference records from BigQuery to display in the Gradio frontend's history dataframe,
    providing users with a summary of recent MLOps pipeline activity.
    
    Args:
        target_columns (List[str]): List of column names to fetch from the BigQuery table.
        bigquery_client (Any): The BigQuery client object.
        table_reference (str): The BigQuery table reference.
        
    Returns:
        List[List[Any]]: A list of formatted rows containing inference metadata for display in the Gradio Dataframe.
    """

    rows = get_recent_inferences(bigquery_client=bigquery_client, table_reference=table_reference,
                                 target_columns=target_columns, limit=10)

    # Gradio's grow.Dataframe expects a list of lists (rows of columns)
    formatted_rows = []
    for row in rows:
        formatted_rows.append([row.get("uuid", ""),
                               row.get("predicted_class", ""),
                               row.get("probability", 0.0),
                               str(row.get("timestamp", "")),
                               row.get("kubernetes_node", ""),
                               row.get("gcs_image_uri", ""),
                               row.get("additional_comment", "")])
    return formatted_rows
