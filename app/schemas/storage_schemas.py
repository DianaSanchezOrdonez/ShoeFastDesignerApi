from pydantic import BaseModel
from typing import List

class BucketCreate(BaseModel):
    collection_name: str

class MoveImagesRequest(BaseModel):
    image_names: List[str]  # Lista de nombres de archivos (ej: "library/shoe_123.png")
    target_bucket_name: str