"""
Script that is used to launch inference using a .onnx file.
"""
import cv2
import numpy as np
from triton_inference_functions import join, dirname, get_images, preprocess, get_inference_server_client, \
    run_neural_network_inference

image_path = join(dirname(dirname(__file__)), "inference_data", "circle_1.png")

# Define client, input and output tensors
client = get_inference_server_client(triton_server_url="localhost:8001")

input_tensor = 'Input-Producer/Placeholders/Images/Placeholder_1:0'
ouput_tensor = 'Outputs/Softmax:0'

# Run preprocessing
preprocessed_image = preprocess(cv2.imread(image_path),
                                height=300,
                                width=300,
                                keep_ratio=True,
                                center=False)

preprocessed_image = np.expand_dims(preprocessed_image, 0)

# Run neural network prediction
prediction = run_neural_network_inference(data=preprocessed_image, client=client, input_tensor=input_tensor,
                                          output_tensor=ouput_tensor)[0]

inference_results = {
    "squares": np.round(prediction[0], 4),
    "circles": np.round(prediction[1], 4),
}

print(inference_results)
