import base64
import json
import uuid
import os
from google.cloud import storage, firestore

# Inicializamos los clientes fuera de la función para mayor velocidad
db = firestore.Client()
storage_client = storage.Client()

def save_generation_background(event, context):
    try:
        # 1. Decodificar el mensaje de Pub/Sub
        pubsub_message = base64.b64decode(event['data']).decode('utf-8')
        data = json.loads(pubsub_message)
        
        user_id = data['user_id']
        project_id = data['project_id']
        image_bytes = base64.b64decode(data['image_base64'])
        
        # 2. Subir a Cloud Storage
        bucket_name = os.environ.get("GCP_BUCKET_NAME")
        bucket = storage_client.bucket(bucket_name)
        
        gen_id = str(uuid.uuid4())
        file_path = f"users/{user_id}/projects/{project_id}/generations/{gen_id}.png"
        blob = bucket.blob(file_path)
        blob.upload_from_string(image_bytes, content_type="image/png")
        
        # 3. Guardar URL en Firestore
        image_url = f"https://storage.googleapis.com/{bucket_name}/{file_path}"
        
        db.collection("projects").document(project_id).collection("generations").add({
            "generation_id": gen_id,
            "image_url": image_url,
            "material_id": data.get("material_id"),
            "created_at": firestore.SERVER_TIMESTAMP
        })

        # 4. Actualizar contador en el proyecto padre
        db.collection("projects").document(project_id).update({
            "generations_count": firestore.Increment(1),
            "updated_at": firestore.SERVER_TIMESTAMP
        })

        print(f"Exito: Generación guardada para proyecto {project_id}")

    except Exception as e:
        print(f"Error procesando mensaje: {str(e)}")
        # No relanzamos el error a menos que queramos reintentos infinitos