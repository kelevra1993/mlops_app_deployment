import os
import uuid
import cv2
import tempfile
import numpy as np

from fastapi import FastAPI, UploadFile, File, Form
from pydantic import BaseModel

# Importing the required logic from our other modules
from app.utilities.inference_utilities import get_inference_server_client, perform_inference
from app.utilities.gcp_utilities import insert_inference_data_in_bigquery, upload_object, storage_client, bigquery_client
from app.utilities.constants import BUCKET_NAME, INFERRED_IMAGE_PREFIX, TABLE_REFERENCE

app = FastAPI(
    title="MLOps Classifier API",
    description="A standalone programmatic API for running inference on images using Triton Inference Server."
)

# Fetch the environment variables required for identifying the replica and connecting to Triton
REPLICA_NAME = os.getenv("REPLICA_NAME", "API_POD_NOT_IDENTIFIED")
TRITON_SERVER_URL = os.getenv("TRITON_SERVER_URL", "localhost:8001")

# Initialize the Triton client once when the app starts
print(f"Initializing Triton client connecting to: {TRITON_SERVER_URL}")
triton_client = get_inference_server_client(TRITON_SERVER_URL)

class InferenceResponse(BaseModel):
    uuid: str
    predicted_class: str
    probability: float
    gcs_uri: str
    message: str

@app.post("/infer", response_model=InferenceResponse)
async def run_inference(
    image: UploadFile = File(...),
    additional_comment: str = Form("")
):
    """
    Endpoint to process an uploaded image, run inference, save the image to GCS, 
    and store the result in BigQuery.
    """
    
    # Generate a unique identifier for this particular inference request
    inference_uuid = str(uuid.uuid4())
    
    # Create a temporary file to save the uploaded image
    # This is required because our GCS upload and cv2 functions expect a local filepath
    temp_image_path = os.path.join(tempfile.gettempdir(), f"{inference_uuid}_{image.filename}")
    
    try:
        # 1. Save the uploaded file to disk
        contents = await image.read()
        with open(temp_image_path, "wb") as f:
            f.write(contents)
            
        # 2. Read the image using OpenCV for Triton preprocessing
        # cv2.imread expects a valid filepath and returns a numpy array
        image_np = cv2.imread(temp_image_path)
        if image_np is None:
            return {"message": "Invalid image format.", "uuid": inference_uuid, "predicted_class": "Error", "probability": 0.0, "gcs_uri": ""}
            
        # 3. Perform inference via Triton
        predicted_class, probability = perform_inference(
            image_np, 
            triton_client,
            'Input-Producer/Placeholders/Images/Placeholder_1:0',
            'Outputs/Softmax:0',
            height=300,
            width=300,
            keep_ratio=True,
            center=False
        )
        
        # 4. Upload the saved image to Google Cloud Storage
        gcs_blob_name = f"{INFERRED_IMAGE_PREFIX}/{inference_uuid}_{image.filename}"
        gcs_uri = upload_object(storage_client, BUCKET_NAME, temp_image_path, gcs_blob_name)
        
        # 5. Format the comment with the required prefix
        prefixed_comment = f"Called By API : {additional_comment}" if additional_comment else "Called By API : "
        
        # 6. Insert the inference metadata into BigQuery
        insert_inference_data_in_bigquery(
            bigquery_client=bigquery_client,
            table_reference=TABLE_REFERENCE,
            uuid_str=inference_uuid,
            predicted_class=predicted_class,
            probability=probability,
            kubernetes_node=REPLICA_NAME,
            gcs_image_uri=gcs_uri,
            additional_comment=prefixed_comment
        )
        
        # Return a structured JSON response to the client
        return InferenceResponse(
            uuid=inference_uuid,
            predicted_class=predicted_class,
            probability=probability,
            gcs_uri=gcs_uri,
            message="Inference completed successfully."
        )
        
    except Exception as e:
        print(f"Error during API inference: {e}")
        return InferenceResponse(
            uuid=inference_uuid,
            predicted_class="Error",
            probability=0.0,
            gcs_uri="",
            message=str(e)
        )
    finally:
        # Always clean up the temporary file to prevent disk space leaks
        if os.path.exists(temp_image_path):
            os.remove(temp_image_path)
