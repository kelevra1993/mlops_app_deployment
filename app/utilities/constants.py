import os

# Simple Expected Image File Extensions
IMAGE_FILE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".tiff")

# Google Cloud Platform Project Constants
PROJECT_ID = "ml-ops-classifier-app"

# Big Query Constants
DATASET_ID = "machine_learning_predictions_euw3"
TABLE_ID = "inference_history"
TABLE_REFERENCE = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"
PREDICTED_INFROMATION_COLUMNS = ["uuid",
                                 "predicted_class",
                                 "probability",
                                 "timestamp",
                                 "kubernetes_node",
                                 "gcs_image_uri",
                                 "additional_comment"]

# Google Cloud Storage Constants
BUCKET_NAME = "machine-learning-ops-images-bucket-2026"
INFERRED_IMAGE_PREFIX = "inferred_image"

# Environment Variables
REPLICA_NAME = os.getenv("REPLICA_NAME", "POD NOT IDENTIFIED")
TRITON_SERVER_URL = os.getenv("TRITON_SERVER_URL", "localhost:8001")