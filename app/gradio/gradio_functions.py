import cv2
import os
import sys

# Ensure the root project directory is in the Python path for imports to work correctly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app.triton_inference.triton_inference_functions import (
    get_images,
    perform_inference,
)


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


def process_image(uploaded_image, selected_inference_image):
    """
    Processes the selected or uploaded image and returns inference results.
    
    Args:
        uploaded_image (str): Filepath to the uploaded image.
        selected_inference_image (str): The filename of the selected image from the dropdown.
        
    Returns:
        tuple: (image_name, score, predicted_class)
    """
    image_name = "Unknown"
    image_to_process = None
    
    if uploaded_image is not None:
        # If user uploaded an image, it takes precedence
        image_name = os.path.basename(uploaded_image)
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
        return "No image selected", 0.0, "N/A"
        
    if image_to_process is None:
        return image_name, 0.0, "Failed to load image"
        
    predicted_class, score = perform_inference(image_to_process)
    
    return image_name, score, predicted_class
