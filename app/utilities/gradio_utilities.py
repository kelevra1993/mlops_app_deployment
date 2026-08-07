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
from app.utilities.gcp_utilities import insert_inference_data_in_bigquery, get_recent_inferences, upload_object
from app.utilities.constants import BUCKET_NAME, INFERRED_IMAGE_PREFIX, TABLE_REFERENCE, PREDICTED_INFROMATION_COLUMNS


def get_default_inference_data_images(data_directory):
    """
    todo update documentation
    """

    if os.path.exists(data_directory):
        return get_images(data_directory, basename=False)

    return []


def process_image(user_image_path, default_image_path, additional_comment, client):
    """
    todo to be properly documented
    """



    # todo move this to it's own function determine_image_to_process
    image_name = "Unknown"
    image_to_process = None
    image_path = None

    if user_image_path is not None:

        # If user uploaded an image, it takes precedence
        image_name = os.path.basename(user_image_path)
        image_path = user_image_path

        # Read image using cv2 (Gradio returns filepath when type='filepath')
        image_to_process = cv2.imread(user_image_path)

    elif default_image_path is not None:
        # Otherwise, use the selected inference data image
        image_name = os.path.basename(default_image_path)
        image_path = default_image_path
        image_to_process = cv2.imread(image_path)
    # todo end of move this to it's own function determine_image_to_process

    # TODO IMPLEMENTATION WILL BE CHANGED TO LOAD ERROR IMAGE WITH MESSAGE
    if image_to_process is None:
        return image_name, 0.0, "Failed to load image", None

    # 1. Run inference
    predicted_class, score = perform_inference(image=image_to_process, client=client,
                                               input_tensor='Input-Producer/Placeholders/Images/Placeholder_1:0',
                                               output_tensor='Outputs/Softmax:0',
                                               height=300, width=300, keep_ratio=True, center=False)


    # todo create function upload_data_to_google_cloud

    # 2. Generate UUID for this inference run
    inference_uuid = str(uuid.uuid4())

    # 3. Upload to Google Cloud Storage
    gcs_blob_name = f"{INFERRED_IMAGE_PREFIX}/{inference_uuid}_{image_name}"
    gcs_uri = upload_object(storage_client, BUCKET_NAME, image_path, gcs_blob_name)

    # 4. Save to BigQuery with the required prefix
    prefixed_comment = f"Called By Gradio : {additional_comment}" if additional_comment else "Called By Gradio : "
    replica_name = os.getenv("REPLICA_NAME", "POD NOT IDENTIFIED")

    insert_inference_data_in_bigquery(
        bigquery_client=bigquery_client,
        table_reference=TABLE_REFERENCE,
        uuid_str=inference_uuid,
        predicted_class=predicted_class,
        probability=score,
        kubernetes_node=replica_name,
        gcs_image_uri=gcs_uri,
        additional_comment=prefixed_comment
    )
    # todo end of create function upload_data_to_google_cloud

    return image_name, score, predicted_class, image_path


def fetch_recent_inferences():
    """
    Fetches the 5 most recent inferences from BigQuery and formats them for the Gradio Dataframe.
    """
    target_cols = ", ".join(PREDICTED_INFROMATION_COLUMNS)
    rows = get_recent_inferences(bigquery_client=bigquery_client, table_reference=TABLE_REFERENCE,
                                 target_columns=target_cols, limit=5)

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
