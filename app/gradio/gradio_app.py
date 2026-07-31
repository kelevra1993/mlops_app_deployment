import gradio as gr
import os
import sys

# Ensure the root project directory is in the Python path for imports to work correctly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from gradio_functions import process_image, get_inference_data_images
from app.triton_inference.triton_inference_functions import get_inference_server_client

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
            submit_btn = gr.Button("Run Inference", variant="primary")
            
        with gr.Column():
            out_image = gr.Image(type="filepath", label="Inferred Image")
            out_image_name = gr.Textbox(label="Image Name")
            out_score = gr.Number(label="Prediction Score")
            out_class = gr.Textbox(label="Predicted Class")
            
    # Connect the UI elements to the processing function
    submit_btn.click(
        fn=lambda uploaded_image, selected_image: process_image(uploaded_image, selected_image, triton_client),
        inputs=[upload_input, dropdown_input],
        outputs=[out_image_name, out_score, out_class, out_image]
    )

    # Mutually exclusive inputs: clear the other when one is changed, but only if the changed input has a value
    upload_input.change(fn=lambda val: None if val is not None else gr.update(), inputs=upload_input, outputs=dropdown_input)
    dropdown_input.change(fn=lambda val: None if val else gr.update(), inputs=dropdown_input, outputs=upload_input)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
