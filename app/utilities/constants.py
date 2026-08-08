import os

# Simple Expected Image File Extensions
IMAGE_FILE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".tiff")

# Google Cloud Platform Project Constants
PROJECT_ID = "ml-ops-classifier-app"

# Big Query Constants
DATASET_ID = "machine_learning_predictions"
TABLE_ID = "inference_history"
TABLE_REFERENCE = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"
PREDICTED_INFROMATION_COLUMNS = ["uuid",
                                 "predicted_class",
                                 "probability",
                                 "timestamp",
                                 "kubernetes_node",
                                 "gcs_image_uri",
                                 "additional_comment"]

# GPU Search Configurations
ZONES_TO_SEARCH = [
    "europe-west1-b",
    "europe-west1-c",
    "europe-west1-d",
    "europe-west4-a",
    "europe-west4-b",
    "europe-west4-c",
    "europe-west3-a",
    "europe-west3-b",
    "europe-west3-c",
    "us-central1-a",
    "us-central1-b",
    "us-central1-c",
    "us-central1-f",
    "us-east1-b",
    "us-east1-c",
    "us-east1-d"
]

GPU_CONFIGURATIONS = [
    {"machine_type": "g2-standard-4", "accelerator_type": "nvidia-l4"},
    {"machine_type": "n1-standard-4", "accelerator_type": "nvidia-tesla-t4"}
]

# Google Cloud Storage Constants
BUCKET_NAME = "machine-learning-ops-images-bucket-2026"
INFERRED_IMAGE_PREFIX = "inferred_image"

# Environment Variables
REPLICA_NAME = os.getenv("REPLICA_NAME", "POD NOT IDENTIFIED")
TRITON_SERVER_URL = os.getenv("TRITON_SERVER_URL", "localhost:8001")