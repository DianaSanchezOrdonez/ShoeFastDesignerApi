from uuid import uuid4
from google.cloud import storage, firestore
from app.core.config import settings
from datetime import datetime
import json
from google.cloud import storage, firestore, pubsub_v1

class ProjectService:
    def __init__(self):
        self.db = firestore.Client()
        self.storage_client = storage.Client()
        # Usamos la variable de entorno para evitar hardcoding
        self.bucket = self.storage_client.bucket(settings.GCS_BUCKET_NAME)
        # Inicializamos Pub/Sub
        self.publisher = pubsub_v1.PublisherClient()
        # El topic path se construye con el ID de tu proyecto y el ID del tópico
        self.topic_path = self.publisher.topic_path(
            settings.PROJECT_ID, 
            settings.PUBSUB_TOPIC_ID
        )

    async def create_project(self, user_id: str, name: str, sketch_bytes: bytes, content_type: str):
        project_id = str(uuid4())
        
        # 1. Subir boceto original a GCS (La única persistencia síncrona)
        blob_path = f"users/{user_id}/projects/{project_id}/original_sketch.jpg"
        blob = self.bucket.blob(blob_path)
        blob.upload_from_string(sketch_bytes, content_type=content_type)
        
        # 2. Preparamos el objeto de retorno 
        project_data = {
            "id": project_id,
            "user_id": user_id,
            "name": name,
            "sketch_url": blob.public_url,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "status": "active",
            "generations_count": 0
        }
        
        # 3. Enviar al worker (Pub/Sub)
        # Es vital enviar un "type" para que el worker sepa qué hacer
        message = {
            "type": "CREATE_PROJECT",
            "payload": project_data
        }
        data = json.dumps(message).encode("utf-8")
        
        try:
            data = json.dumps(message).encode("utf-8")
            # Esto ya no fallará porque definimos publisher arriba
            self.publisher.publish(self.topic_path, data)
            print(f"[PubSub] Evento enviado para proyecto: {name}")
        except Exception as e:
            print(f"[PubSub Error] No se pudo enviar el evento: {e}")
            
        return project_data

    async def get_user_projects(self, user_id: str):
        # Obtener todos los proyectos pertenecientes al usuario
        projects_ref = self.db.collection("projects").where("user_id", "==", user_id)
        docs = projects_ref.stream()
        
        return [doc.to_dict() for doc in docs]