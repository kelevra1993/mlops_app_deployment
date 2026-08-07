import os
import sys

import gradio as gr

from google.cloud import bigquery, storage
from pathlib import Path

# Ensure the root project directory is in the Python path for imports to work correctly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app.utilities.inference_utilities import get_inference_server_client
from app.utilities.constants import (PROJECT_ID,
                                     TABLE_REFERENCE,
                                     BUCKET_NAME,
                                     INFERRED_IMAGE_PREFIX,
                                     PREDICTED_INFROMATION_COLUMNS,
                                     REPLICA_NAME,
                                     TRITON_SERVER_URL)
from app.utilities.gradio_utilities import process_image, get_default_inference_data_images, fetch_recent_inferences

# Initialize the BigQuery client. It will automatically use the default credentials
# available in the environment (e.g. from the service account attached to the GKE node).
bigquery_client = bigquery.Client(project=PROJECT_ID)

# Initialize the Google Cloud Storage client. Like BigQuery, this will use the default credentials
# available in the environment.
storage_client = storage.Client(project=PROJECT_ID)

# Prepare default images for the dropdown
default_data_directory = Path(os.getcwd()).parent / "data"
inference_images = get_default_inference_data_images(data_directory=str(default_data_directory))
image_default_choices = [str(os.path.basename(image_path)) for image_path in inference_images]

print(f"Initializing Triton Client Connecting To: {TRITON_SERVER_URL}")
triton_client = get_inference_server_client(TRITON_SERVER_URL)

with gr.Blocks(title="Triton Inference App") as demo:
    gr.Markdown(f"**Replica:** {REPLICA_NAME}")
    gr.Markdown("# Image Classification Inference")
    gr.Markdown("Upload your own image or select one from the `inference_data` folder to run inference.")
    
    # Definition Of First Row
    with gr.Row():
        # First cell contains :
        # - Area where the user image is uploaded
        # -
        with gr.Column():
            upload_input = gr.Image(type="filepath", label="Upload your own image")
            dropdown_input = gr.Dropdown(choices=image_default_choices, label="Or Select From Default Inference Data")
            comment_input = gr.Textbox(label="Additional Comment", placeholder="Enter any extra details here...")
            submit_button = gr.Button("Run Inference", variant="primary")

        # Second cell contains image that was used for inference
        with gr.Column():
            output_image = gr.Image(type="filepath", label="Inferred Image")
            output_image_name = gr.Textbox(label="Image Name")
            out_score = gr.Number(label="Prediction Score")
            out_class = gr.Textbox(label="Predicted Class")

    # Connect the UI elements to the processing function
    submit_button.click(
        fn=lambda uploaded, selected, comment: process_image(
            user_image_path=uploaded,
            default_image_path=selected,
            additional_comment=comment,
            client=triton_client,
            inferred_image_prefix=INFERRED_IMAGE_PREFIX,
            bucket_name=BUCKET_NAME,
            table_reference=TABLE_REFERENCE,
            bigquery_client=bigquery_client,
            storage_client=storage_client
        ),
        inputs=[upload_input, dropdown_input, comment_input],
        outputs=[output_image_name, out_score, out_class, output_image]
    )

    # Mutually exclusive inputs: clear the other when one is changed, but only if the changed input has a value
    upload_input.change(fn=lambda val: None if val is not None else gr.update(), inputs=upload_input,
                        outputs=dropdown_input)
    dropdown_input.change(fn=lambda val: None if val else gr.update(), inputs=dropdown_input, outputs=upload_input)

    gr.Markdown("---")
    gr.Markdown("## Recent Inference History")
    gr.Markdown(
        "Click the button below to retrieve the last 5 records stored in the BigQuery `inference_history` table.")

    fetch_button = gr.Button("Get Last 5 Inferences")
    recent_table = gr.Dataframe(
        headers=["UUID", "Predicted Class", "Probability", "Timestamp", "Node", "GCS URI", "Comment"])

    fetch_button.click(
        fn=lambda: fetch_recent_inferences(
            target_columns=PREDICTED_INFROMATION_COLUMNS,
            bigquery_client=bigquery_client,
            table_reference=TABLE_REFERENCE
        ),
        inputs=[],
        outputs=[recent_table]
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
