import gradio as gr
import os

from gradio_functions import process_image, get_inference_data_images

# Prepare images for the dropdown
inference_images = get_inference_data_images()
image_choices = [os.path.basename(img) for img in inference_images]

with gr.Blocks(title="Triton Inference App") as demo:
    gr.Markdown("# Image Classification Inference")
    gr.Markdown("Upload your own image or select one from the `inference_data` folder to run inference.")
    
    with gr.Row():
        with gr.Column():
            upload_input = gr.Image(type="filepath", label="Upload your own image")
            dropdown_input = gr.Dropdown(choices=image_choices, label="Or select from inference data")
            submit_btn = gr.Button("Run Inference", variant="primary")
            
        with gr.Column():
            out_image_name = gr.Textbox(label="Image Name")
            out_score = gr.Number(label="Prediction Score")
            out_class = gr.Textbox(label="Predicted Class")
            
    # Connect the UI elements to the processing function
    submit_btn.click(
        fn=process_image,
        inputs=[upload_input, dropdown_input],
        outputs=[out_image_name, out_score, out_class]
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
