import os
import cv2
import numpy as np

from random import shuffle
from os.path import join, dirname, basename

import tritonclient.grpc as nvclient


def preprocess(image, height, width, keep_ratio=False, center=False):
    '''
    :param image: a numpy array of an image in BLUE, GREEN, RED opened by OpenCV
    :param height: desired output height
    :param width: desired output width
    :param keep_ratio: boolean that decides whether or not we keep the aspect ratio of an image
                    by default keep_ratio is False.
                    In the case where we decide to keep the aspect ratio, black bars will either be appended
                    on the right hand side of the images or on the bottom of the image to fit our desired height and width
    :param center: boolean that decides if image is centered while applying keep_ratio
    :return: processed_image: numpy array of desired height and width
    '''

    processed_image = None

    if keep_ratio:
        image_height, image_width, _ = image.shape
        image_ratio = (image_height / image_width)

        if center:

            maximum_size = max([image_height, image_width])
            processed_image = np.zeros((maximum_size, maximum_size, 3), dtype=image.dtype)

            start_x = int((maximum_size - image_width) / 2)
            start_y = int((maximum_size - image_height) / 2)

            processed_image[start_y:start_y + image_height, start_x:start_x + image_width, :] = image[:image_height,
            :image_width, :]
            processed_image = cv2.resize(processed_image, (width, height))

        else:
            if image_ratio > 1:
                new_width = int(height / image_ratio)
                image = cv2.resize(image, (new_width, height))
                stack = np.zeros((height, (width - new_width), 3), dtype=np.uint8)
                processed_image = np.hstack((image, stack))

            if image_ratio < 1:
                new_height = int(width * image_ratio)
                image = cv2.resize(image, (width, new_height))
                stack = np.zeros(((height - new_height), width, 3), dtype=np.uint8)
                processed_image = np.vstack((image, stack))

            if image_ratio == 1:
                processed_image = cv2.resize(image, (width, height))
    else:
        processed_image = cv2.resize(image, (width, height))

    return processed_image


def get_inference_server_client(triton_server_url):
    """
    Function that gets inference server client url.
    In our case when we are inferring locally we binded triton inference server port 8001 to our own port 8001
    you can find that information in the docker compose up file therefore
    triton_server_url is  "localhost:8001" when running inference locally
    """
    return nvclient.InferenceServerClient(triton_server_url, ssl=False)


def run_neural_network_inference(data,
                                 client,
                                 input_tensor,
                                 output_tensor):
    """
    Function that runs neural network inference
    :param data: input image
    :param client: triton inference server client
    :param input_tensor: input tensor of the neural network
    :param output_tensor: output tensor of the neural network
    """

    inputs = [nvclient.InferInput(input_tensor, data.shape, "FP32")]
    inputs[0].set_data_from_numpy(data.astype(np.float32))

    outputs = [nvclient.InferRequestedOutput(output_tensor)]

    results = client.infer(model_name="neural_network_model", inputs=inputs, outputs=outputs)

    return results.as_numpy(output_tensor)


def get_images(path, basename=False, sort=False, mix=False, coherence=False):
    """
    Function that returns images from a given directory path
    :param basename: boolean if we only want to get simple image file name instead of full image file name
    :param sort: boolean to sort image files that have been found
    :param mix: boolean that allows to shuffle image files that have been found
    :param coherence: boolean in order to check that image file is not a 0 octet image file
    :return image: list of image files
    """
    if coherence:
        if basename:
            images = [file for file in os.listdir(path) if
                      file.endswith(('.jpg', '.png', '.jpeg', '.tiff')) and os.stat(join(path, file)).st_size != 0]
        else:
            images = [join(path, file) for file in os.listdir(path) if
                      file.endswith(('.jpg', '.png', '.jpeg', '.tiff')) and os.stat(join(path, file)).st_size != 0]
    else:
        if basename:
            images = [file for file in os.listdir(path) if
                      file.endswith(('.jpg', '.png', '.jpeg', '.tiff'))]
        else:
            images = [join(path, file) for file in os.listdir(path) if
                      file.endswith(('.jpg', '.png', '.jpeg', '.tiff'))]
    if mix:
        shuffle(images)

    if sort:
        images = sorted(images)

    return images
