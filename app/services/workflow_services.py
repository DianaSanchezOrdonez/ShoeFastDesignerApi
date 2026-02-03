from uuid import uuid4
from google.cloud import storage, firestore
from app.core.config import settings
from datetime import datetime, timedelta
import json
from google.cloud import storage, firestore, pubsub_v1
from google.oauth2 import service_account
import os
import urllib.parse

class WorkflowService:
    def __init__(self):
        self.creds = service_account.Credentials.from_service_account_file(
            settings.GOOGLE_APPLICATION_CREDENTIALS
        )
        self.db = firestore.Client(credentials=self.creds, project=settings.PROJECT_ID)
        self.storage_client = storage.Client(credentials=self.creds, project=settings.PROJECT_ID)

        self.bucket_name = settings.GCS_BUCKET_NAME
        self.bucket = self.storage_client.bucket(self.bucket_name)
        
        self.publisher = pubsub_v1.PublisherClient(credentials=self.creds)
        self.topic_path = self.publisher.topic_path(settings.PROJECT_ID, settings.PUBSUB_TOPIC_ID)

    async def create_workflow(
        self,
        user_id: str,
        name: str,
        sketch_bytes: bytes,
        content_type: str
    ):
        workflow_id = str(uuid4())

        blob_path = f"users/{user_id}/workflows/{workflow_id}/original_sketch.jpg"
        blob = self.bucket.blob(blob_path)
        blob.upload_from_string(sketch_bytes, content_type=content_type)

        workflow_data = {
            "id": workflow_id,
            "user_id": user_id,
            "name": name,
            "sketch_blob_path": blob_path,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "status": "active",
            "generations_count": 0
        }

        message = {
            "type": "CREATE_WORKFLOW",
            "payload": workflow_data
        }

        try:
            self.publisher.publish(
                self.topic_path,
                json.dumps(message).encode("utf-8")
            )
            print(f"[PubSub] Evento enviado para proyecto: {name}")
        except Exception as e:
            print(f"[PubSub Error] {e}")

        return workflow_data


    async def get_user_workflows(self, user_id: str):
        workflows_ref = self.db.collection("workflows").where("user_id", "==", user_id)
        docs = workflows_ref.stream()
        
        workflows = []
        for doc in docs:
            workflow = doc.to_dict()
            workflow["id"] = doc.id
            
            blob_path = workflow.get("sketch_blob_path")
            if blob_path:
                blob = self.bucket.blob(blob_path)
                workflow["sketch_url"] = blob.generate_signed_url(
                    version="v4",
                    expiration=timedelta(minutes=60),
                    method="GET"
                )
            
            workflows.append(workflow)
        
        return workflows
    
    def _get_signed_url_from_blob_path(self, blob_path: str):
        if not blob_path:
            return None

        try:
            blob = self.bucket.blob(blob_path)
            return blob.generate_signed_url(
                version="v4",
                expiration=timedelta(minutes=60),
                method="GET"
            )
        except Exception as e:
            print(f"[WorkflowService] Error firmando {blob_path}: {e}")
            return None
    
    async def get_workflow_details(self, workflow_id: str, user_id: str):
        workflow_ref = self.db.collection("workflows").document(workflow_id)
        doc = workflow_ref.get()

        if not doc.exists:
            return None

        workflow_data = doc.to_dict()

        if workflow_data.get("user_id") != user_id:
            return None

        workflow_data["sketch_url"] = self._get_signed_url_from_blob_path(
            workflow_data.get("sketch_blob_path")
        )

        generations_ref = (
            workflow_ref
            .collection("generations")
            .order_by("created_at", direction=firestore.Query.DESCENDING)
        )

        generations = []
        for gen_doc in generations_ref.stream():
            gen_data = gen_doc.to_dict()

            gen_data["image_url"] = self._get_signed_url_from_blob_path(
                gen_data.get("image_blob_path")
            )

            if isinstance(gen_data.get("created_at"), datetime):
                gen_data["created_at"] = gen_data["created_at"].isoformat()

            generations.append(gen_data)

        return {
            "workflow": workflow_data,
            "generations": generations
        }
    
    async def get_workflows_with_latest_generation(self, user_id: str):
        workflow_docs = (
            self.db
            .collection("workflows")
            .where("user_id", "==", user_id)
            .order_by("created_at", direction=firestore.Query.DESCENDING)
            .stream()
        )
        
        result = []

        for doc in workflow_docs:
            workflow = doc.to_dict()
            workflow["id"] = doc.id

            workflow["sketch_url"] = self._get_signed_url_from_blob_path(
                workflow.get("sketch_url") or workflow.get("sketch_blob_path")
            )

            generations_ref = (
                self.db
                .collection("workflows")
                .document(doc.id)
                .collection("generations")
                .order_by("created_at", direction=firestore.Query.DESCENDING)
                .limit(1)
            )

            gen_docs = generations_ref.stream()
            
            latest_generation = None
            
            for gen_doc in gen_docs:
                gen_data = gen_doc.to_dict()
                gen_data["id"] = gen_doc.id
                
                gen_data["image_url"] = self._get_signed_url_from_blob_path(
                    gen_data.get("image_url") or gen_data.get("image_blob_path")
                )

                if isinstance(gen_data.get("created_at"), datetime):
                    gen_data["created_at"] = gen_data["created_at"].isoformat()
                
                latest_generation = gen_data

            result.append({
                **workflow, # Aplanamos el workflow para que sea más fácil de usar en el frontend
                "latest_generation": latest_generation
            })
            
        return result
    
    def generate_download_url(self, blob_name: str):
        blob = self.bucket.blob(blob_name)
        filename = os.path.basename(blob_name)
        
        disposition = f'attachment; filename="{filename}"'
        disposition = urllib.parse.quote(disposition)

        url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=15),
            method="GET",
            response_disposition=disposition,
        )
        
        return {"download_url": url}


