import os
from google.cloud import bigquery
from datetime import datetime

# Initialize the BigQuery client. It will automatically use the default credentials 
# available in the environment (e.g. from the service account attached to the GKE node).
client = bigquery.Client(project="ml-ops-classifier-app")

DATASET_ID = "machine_learning_predictions_euw3"
TABLE_ID = "inference_history"
TABLE_REF = f"ml-ops-classifier-app.{DATASET_ID}.{TABLE_ID}"

def insert_inference_data(
    uuid_str: str, 
    predicted_class: str, 
    probability: float, 
    kubernetes_node: str, 
    gcs_image_uri: str, 
    additional_comment: str
):
    """
    Inserts a single inference record into the BigQuery inference_history table.
    
    Args:
        uuid_str (str): A unique identifier for the inference run.
        predicted_class (str): The class predicted by the model (e.g. 'circles' or 'squares').
        probability (float): The confidence score of the prediction.
        kubernetes_node (str): The name of the node/replica processing this request.
        gcs_image_uri (str): The Google Cloud Storage URI where the inferred image was saved.
        additional_comment (str): Any extra comments to store alongside the record.
    """
    
    # We construct the row dictionary matching the schema defined in Terraform.
    # The timestamp is generated right here before insertion.
    row_to_insert = {
        "uuid": uuid_str,
        "predicted_class": predicted_class,
        "probability": float(probability),
        "timestamp": datetime.utcnow().isoformat(),
        "kubernetes_node": kubernetes_node,
        "gcs_image_uri": gcs_image_uri,
        "additional_comment": additional_comment
    }
    
    # insert_rows_json streams data directly into BigQuery.
    errors = client.insert_rows_json(TABLE_REF, [row_to_insert])
    
    if errors:
        print(f"Encountered errors while inserting rows into BigQuery: {errors}")
    else:
        print(f"Successfully inserted inference record {uuid_str} into BigQuery.")

def get_recent_inferences(limit: int = 5):
    """
    Retrieves the most recent inference records from BigQuery.
    
    Args:
        limit (int): The maximum number of records to retrieve. Default is 5.
        
    Returns:
        list[dict]: A list of dictionary objects representing the rows.
    """
    # We use a SQL query to fetch the latest rows by ordering the timestamp descending.
    query = f"""
        SELECT 
            uuid, predicted_class, probability, timestamp, kubernetes_node, gcs_image_uri, additional_comment
        FROM 
            `{TABLE_REF}`
        ORDER BY 
            timestamp DESC
        LIMIT {limit}
    """
    
    try:
        query_job = client.query(query)
        results = query_job.result() # Wait for the job to complete
        
        # Convert the BigQuery Row objects to standard python dictionaries
        rows = [dict(row) for row in results]
        return rows
    except Exception as e:
        print(f"Error retrieving recent inferences from BigQuery: {e}")
        return []
