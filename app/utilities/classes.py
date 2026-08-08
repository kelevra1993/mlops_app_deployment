from pydantic import BaseModel


class InferenceResponse(BaseModel):
    """
    Data model representing the standard JSON response returned by the inference API.
    
    This structured format ensures clients receive consistent information about their
    prediction request, including the model's confidence and where the processed
    data is stored in the MLOps pipeline.
    """
    uuid: str
    predicted_class: str
    probability: float
    gcs_uri: str
    message: str
