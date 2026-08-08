import os
import uuid
import cv2
import sys
import tempfile

from google.cloud import bigquery, storage
from fastapi import FastAPI, UploadFile, File, Form

# Ensure the root project directory is in the Python path for imports to work correctly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Importing the required logic from our other modules
from app.utilities.inference_utilities import get_inference_server_client, perform_inference
from app.utilities.gcp_utilities import insert_inference_data_in_bigquery, upload_object
from app.utilities.constants import (PROJECT_ID,
                                     TABLE_REFERENCE,
                                     BUCKET_NAME,
                                     INFERRED_IMAGE_PREFIX,
                                     PREDICTED_INFROMATION_COLUMNS,
                                     REPLICA_NAME,
                                     TRITON_SERVER_URL)
from app.utilities.classes import InferenceResponse

app = FastAPI(
    title="MLOps Classifier API",
    description="A standalone API For Running Inference On Images Using Triton Inference Server.")

# Initialize the BigQuery client. It will automatically use the default credentials
# available in the environment (e.g. from the service account attached to the GKE node).
bigquery_client = bigquery.Client(project=PROJECT_ID)

# Initialize the Google Cloud Storage client. Like BigQuery, this will use the default credentials
# available in the environment.
storage_client = storage.Client(project=PROJECT_ID)

# Initialize the Triton client once when the app starts
print(f"Initializing Triton client connecting to: {TRITON_SERVER_URL}")
triton_client = get_inference_server_client(TRITON_SERVER_URL)


@app.post("/infer", response_model=InferenceResponse)
async def run_inference(image: UploadFile = File(...), additional_comment: str = Form("")) -> InferenceResponse:
    """
    Handles POST requests to the API for performing image classification using the Triton inference backend.
    
    This function acts as the programmatic entry point for the MLOps pipeline. It receives an uploaded image,
    runs it through the Triton Inference Server, stores the original image in Google Cloud Storage, and logs 
    the prediction results in BigQuery for auditing and analytics.
    
    Args:
        image (UploadFile): The image file uploaded by the client.
        additional_comment (str): Optional context or comment provided by the client.
        
    Returns:
        InferenceResponse: A structured response containing the prediction result, UUID, and Google Cloud Storage URI.
    """

    # Generate a unique identifier for this particular inference request
    inference_uuid = str(uuid.uuid4())

    # Create a temporary file to save the uploaded image
    # This is required because our GCS upload and cv2 functions expect a local filepath
    temporary_image_path = os.path.join(tempfile.gettempdir(), f"{inference_uuid}_{image.filename}")

    try:
        # 1. Save the uploaded file to disk
        contents = await image.read()
        with open(temporary_image_path, "wb") as f:
            f.write(contents)

        # 2. Read the image using OpenCV for Triton preprocessing
        # cv2.imread expects a valid filepath and returns a numpy array
        image_numpy_array = cv2.imread(temporary_image_path)
        if image_numpy_array is None:
            return InferenceResponse(message="Invalid image format.", uuid=inference_uuid,
                                     predicted_class="Error", probability=0.0, gcs_uri="")

        # 3. Perform inference via Triton
        predicted_class, probability = perform_inference(
            image=image_numpy_array,
            client=triton_client,
            input_tensor='Input-Producer/Placeholders/Images/Placeholder_1:0',
            output_tensor='Outputs/Softmax:0',
            height=300, width=300, keep_ratio=True, center=False)

        # 4. Upload the saved image to Google Cloud Storage
        gcs_blob_name = f"{INFERRED_IMAGE_PREFIX}/{inference_uuid}_{image.filename}"
        gcs_uri = upload_object(storage_client, BUCKET_NAME, temporary_image_path, gcs_blob_name)

        # 5. Format the comment with the required prefix
        prefixed_comment = f"Called By API : {additional_comment}" if additional_comment else "Called By API : "

        # 6. Insert the inference metadata into BigQuery
        insert_inference_data_in_bigquery(
            bigquery_client=bigquery_client, table_reference=TABLE_REFERENCE,
            uuid_str=inference_uuid, predicted_class=predicted_class,
            probability=probability, kubernetes_node=REPLICA_NAME,
            gcs_image_uri=gcs_uri, additional_comment=prefixed_comment)

        # Return a structured JSON response to the client
        return InferenceResponse(
            uuid=inference_uuid, predicted_class=predicted_class,
            probability=probability, gcs_uri=gcs_uri,
            message="Inference completed successfully.")

    except Exception as e:
        print(f"Error during API inference: {e}")
        return InferenceResponse(
            uuid=inference_uuid, predicted_class="Error",
            probability=0.0, gcs_uri="", message=str(e))
    finally:
        # Always clean up the temporary file to prevent disk space leaks
        if os.path.exists(temporary_image_path):
            os.remove(temporary_image_path)
