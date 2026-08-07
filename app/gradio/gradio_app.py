import gradio as gr
import os
import sys

# Ensure the root project directory is in the Python path for imports to work correctly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app.utilities.gradio_functions import process_image, get_inference_data_images, fetch_recent_inferences
from app.triton_inference.triton_inference_functions import get_inference_server_client

from app.utilities.constants import PROJECT_ID, TABLE_REFERENCE, BUCKET_NAME, INFERRED_IMAGE_PREFIX

# Initialize the BigQuery client. It will automatically use the default credentials
# available in the environment (e.g. from the service account attached to the GKE node).
bigquery_client = bigquery.Client(project=PROJECT_ID)

# Initialize the Google Cloud Storage client. Like BigQuery, this will use the default credentials
# available in the environment.
storage_client = storage.Client(project=PROJECT_ID)


# Prepare images for the dropdown
inference_images = get_inference_data_images()
image_choices = [os.path.basename(img) for img in inference_images]

replica_name = os.getenv("REPLICA_NAME", "POD NOT IDENTIFIED")
triton_server_url = os.getenv("TRITON_SERVER_URL", "localhost:8001")

print(f"Initializing Triton client connecting to: {triton_server_url}")
triton_client = get_inference_server_client(triton_server_url)

with gr.Blocks(title="Triton Inference App") as demo:
    gr.Markdown(f"**Replica:** {replica_name}")
    gr.Markdown("# Image Classification Inference")
    gr.Markdown("Upload your own image or select one from the `inference_data` folder to run inference.")
    
    with gr.Row():
        with gr.Column():
            upload_input = gr.Image(type="filepath", label="Upload your own image")
            dropdown_input = gr.Dropdown(choices=image_choices, label="Or select from inference data")
            comment_input = gr.Textbox(label="Additional Comment", placeholder="Enter any extra details here...")
            submit_btn = gr.Button("Run Inference", variant="primary")
            
        with gr.Column():
            out_image = gr.Image(type="filepath", label="Inferred Image")
            out_image_name = gr.Textbox(label="Image Name")
            out_score = gr.Number(label="Prediction Score")
            out_class = gr.Textbox(label="Predicted Class")
            
    # Connect the UI elements to the processing function
    submit_btn.click(
        fn=lambda uploaded, selected, comment: process_image(uploaded, selected, comment, triton_client),
        inputs=[upload_input, dropdown_input, comment_input],
        outputs=[out_image_name, out_score, out_class, out_image]
    )

    # Mutually exclusive inputs: clear the other when one is changed, but only if the changed input has a value
    upload_input.change(fn=lambda val: None if val is not None else gr.update(), inputs=upload_input, outputs=dropdown_input)
    dropdown_input.change(fn=lambda val: None if val else gr.update(), inputs=dropdown_input, outputs=upload_input)

    gr.Markdown("---")
    gr.Markdown("## Recent Inference History")
    gr.Markdown("Click the button below to retrieve the last 5 records stored in the BigQuery `inference_history` table.")
    
    fetch_btn = gr.Button("Get Last 5 Inferences")
    recent_table = gr.Dataframe(headers=["UUID", "Predicted Class", "Probability", "Timestamp", "Node", "GCS URI", "Comment"])
    
    fetch_btn.click(
        fn=fetch_recent_inferences,
        inputs=[],
        outputs=[recent_table]
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
