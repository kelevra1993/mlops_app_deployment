import cv2
import os
import sys
import uuid

# Ensure the root project directory is in the Python path for imports to work correctly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app.utilities.inference_utilities import (
    get_images,
    perform_inference,
)
from app.bigquery.client import insert_inference_data, get_recent_inferences
from app.gcs.client import upload_inferred_image

def get_inference_data_images():
    """
    Retrieves the list of image paths available in the inference_data directory.

    Returns:
        list: A list of absolute file paths to the inference images.
    """
    # Build the path to app/inference_data
    current_dir = os.path.dirname(__file__)
    inference_data_dir = os.path.join(os.path.dirname(current_dir), "inference_data")
    
    if os.path.exists(inference_data_dir):
        # Use get_images imported from triton_inference_functions
        return get_images(inference_data_dir, basename=False)
    
    return []


def process_image(uploaded_image, selected_inference_image, additional_comment, client):
    """
    Processes the selected or uploaded image and returns inference results.
    It also uploads the image to GCS and saves the record to BigQuery.
    
    Args:
        uploaded_image (str): Filepath to the uploaded image.
        selected_inference_image (str): The filename of the selected image from the dropdown.
        additional_comment (str): The user's input from the new comment Textbox.
        client: Triton Inference Server client
        
    Returns:
        tuple: (image_name, score, predicted_class, image_path)
    """
    image_name = "Unknown"
    image_to_process = None
    image_path = None
    
    if uploaded_image is not None:
        # If user uploaded an image, it takes precedence
        image_name = os.path.basename(uploaded_image)
        image_path = uploaded_image
        # Read image using cv2 (Gradio returns filepath when type='filepath')
        image_to_process = cv2.imread(uploaded_image)
    elif selected_inference_image is not None and selected_inference_image != "":
        # Otherwise, use the selected inference data image
        current_dir = os.path.dirname(__file__)
        inference_data_dir = os.path.join(os.path.dirname(current_dir), "inference_data")
        
        image_name = selected_inference_image
        image_path = os.path.join(inference_data_dir, selected_inference_image)
        if os.path.exists(image_path):
            image_to_process = cv2.imread(image_path)
    else:
        return "No image selected", 0.0, "N/A", None
        
    if image_to_process is None:
        return image_name, 0.0, "Failed to load image", None
        
    # 1. Run inference
    predicted_class, score = perform_inference(
        image_to_process, 
        client,
        'Input-Producer/Placeholders/Images/Placeholder_1:0',
        'Outputs/Softmax:0',
        height=300,
        width=300,
        keep_ratio=True,
        center=False
    )
    
    # 2. Generate UUID for this inference run
    inference_uuid = str(uuid.uuid4())
    
    # 3. Upload to Google Cloud Storage
    gcs_blob_name = f"{inference_uuid}_{image_name}"
    gcs_uri = upload_inferred_image(image_path, gcs_blob_name)
    
    # 4. Save to BigQuery with the required prefix
    prefixed_comment = f"Called By Gradio : {additional_comment}" if additional_comment else "Called By Gradio : "
    replica_name = os.getenv("REPLICA_NAME", "POD NOT IDENTIFIED")
    
    insert_inference_data(
        uuid_str=inference_uuid,
        predicted_class=predicted_class,
        probability=score,
        kubernetes_node=replica_name,
        gcs_image_uri=gcs_uri,
        additional_comment=prefixed_comment
    )
    
    return image_name, score, predicted_class, image_path

def fetch_recent_inferences():
    """
    Fetches the 5 most recent inferences from BigQuery and formats them for the Gradio Dataframe.
    """
    rows = get_recent_inferences(limit=5)
    
    # Gradio's gr.Dataframe expects a list of lists (rows of columns)
    formatted_rows = []
    for r in rows:
        formatted_rows.append([
            r.get("uuid", ""),
            r.get("predicted_class", ""),
            r.get("probability", 0.0),
            str(r.get("timestamp", "")),
            r.get("kubernetes_node", ""),
            r.get("gcs_image_uri", ""),
            r.get("additional_comment", "")
        ])
    return formatted_rows
