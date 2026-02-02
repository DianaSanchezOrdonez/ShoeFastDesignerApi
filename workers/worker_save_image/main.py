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
        
        msg_type = data.get("type")
        payload = data.get("payload", data)
        
        # Caso 1: Crear proyecto
        if msg_type == "CREATE_PROJECT":
            project_id = payload.get('id')
            if not project_id:
                print("Error: No se encontró ID en el payload de creación")
                return

            db.collection("projects").document(project_id).set(payload)
            print(f"Proyecto {payload.get('name')} guardado exitosamente.")
        
        # Caso 2: Guardar generación de imagen
        elif msg_type == "SAVE_GENERATION":
            user_id = payload.get('user_id')
            project_id = payload.get('project_id')
            
            if not user_id or not project_id:
                print(f"Error: Faltan IDs en el mensaje. User: {user_id}, Project: {project_id}")
                return

            image_bytes = base64.b64decode(payload['image_base64'])
            
            # 2. Subir a Cloud Storage
            bucket_name = os.environ.get("GCS_BUCKET_NAME")
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
                "material_id": payload.get("material_id"),
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