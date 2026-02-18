from google.cloud import storage
from google.oauth2 import service_account
from google.api_core.exceptions import GoogleAPIError
from app.core.config import settings
from datetime import timedelta

class ImageStorageService:
    def __init__(self):
        creds = service_account.Credentials.from_service_account_file(
            settings.GOOGLE_APPLICATION_CREDENTIALS
        )
        
        self.client = storage.Client(
            credentials=creds, 
            project=settings.PROJECT_ID
        )
        self.bucket_name = settings.GCS_BUCKET_NAME
        
    def list_images(self, user_uid: str, prefix: str = None):
        try:
            bucket_name = self._get_user_bucket_name(user_uid)
            bucket = self.client.bucket(bucket_name)
            
            search_prefix = prefix if prefix is not None else ""
            blobs = bucket.list_blobs(prefix=prefix)
            
            image_list = []
            for blob in blobs:
                if blob.name.endswith('/') or blob.name.endswith('.keep'):
                    continue
                
                url = blob.generate_signed_url(
                    version="v4",
                    expiration=timedelta(minutes=60),
                    method="GET",
                )
                
                image_list.append({
                    "name": blob.name.replace(search_prefix, ""),
                    "url": url,
                    "updated": blob.updated.isoformat() if blob.updated else None
                })
                
            # Ordenar por fecha de creación (más recientes primero)
            image_list.sort(key=lambda x: x['updated'], reverse=True)
            
            return image_list
        except Exception as e:
            print(f"Error listando con UID {user_uid}: {e}")
            return []
        
    def _get_user_bucket_name(self, user_uid: str) -> str:
        """Centraliza la regla de nombres: siempre 10 chars + sufijo main"""
        user_id_clean = user_uid[:10].lower()
        return f"sfd-user-{user_id_clean}-main"

    def get_or_create_user_bucket(self, user_uid: str):
        try:
            bucket_name = self._get_user_bucket_name(user_uid)
            bucket = self.client.lookup_bucket(bucket_name)
            
            if bucket is None:
                print(f"[Storage] Creando bucket: {bucket_name}")
                bucket = self.client.create_bucket(bucket_name, location="US")
                bucket.labels = {"owner": user_uid[:10].lower(), "type": "main"}
                bucket.patch()
            
            return bucket.name
        except Exception as e:
            print(f"[Storage] Error: {e}")
            raise e
    
    def save_image(self, user_uid: str, image_bytes: bytes, filename: str, folder: str = None):
        try:
            # PASO 1: Aseguramos el bucket (si no existe, se crea AQUÍ)
            bucket_name = self.get_or_create_user_bucket(user_uid)
            bucket = self.client.bucket(bucket_name)

            # PASO 2: Definimos la ruta (en raíz o en carpeta)
            path = f"{folder}/{filename}" if folder else filename
            blob = bucket.blob(path)

            # PASO 3: Subimos la imagen
            blob.upload_from_string(image_bytes, content_type="image/png")
            
            return blob.name
        except Exception as e:
            print(f"[Storage] Error al guardar: {e}")
            raise e
        
    def create_collection_folder(self, user_uid: str, collection_name: str):
        try:
            # PASO 1: Aseguramos el bucket (si es usario nuevo, se crea AQUÍ)
            bucket_name = self.get_or_create_user_bucket(user_uid)
            bucket = self.client.bucket(bucket_name)

            # PASO 2: Marcador de carpeta
            folder_name = collection_name.lower().strip().replace(" ", "-")
            marker_blob = bucket.blob(f"{folder_name}/.keep")
            marker_blob.upload_from_string("") 
            
            return folder_name
        except Exception as e:
            raise e

    def move_blob(self, source_blob_name: str, dest_bucket_name: str):
        """Copia el archivo al nuevo destino y lo elimina del origen."""
        try:
            source_bucket = self.client.bucket(self.bucket_name) # bucket por defecto
            source_blob = source_bucket.blob(source_blob_name)
            
            dest_bucket = self.client.bucket(dest_bucket_name)
            
            new_name = os.path.basename(source_blob_name)
        
            # Copia interna en los servidores de Google
            new_blob = source_bucket.copy_blob(
                source_blob, dest_bucket, new_name 
            )
            
            # Si la copia es exitosa, eliminamos el original
            if new_blob:
                source_blob.delete()
                return True
            return False
        except Exception as e:
            print(f"[ImageStorageService] Error al mover: {e}")
            raise
    
    def list_buckets(self, bucket_name: str):
        """
        Lista los 'folders' (prefijos) virtuales en el bucket.
        """
        from google.cloud import storage
        
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        
        # El delimitador '/' le dice a GCS que trate los prefijos como carpetas
        blobs = client.list_blobs(bucket_name, delimiter='/')
        
        # Consumir el iterador para que GCS llene los prefixes
        list(blobs) 
        
        # blobs.prefixes contiene los nombres de las "carpetas" (ej: "Mules/", "Verano/")
        collections = []
        for prefix in blobs.prefixes:
            # Limpiamos el nombre (quitamos la barra diagonal final)
            clean_name = prefix.rstrip('/')
            collections.append({
                "name": clean_name,
                "count": 0  # Opcional: podrías contar cuántos archivos hay dentro
            })
            
        return collections
    
    def generate_download_url(self, bucket_name: str, blob_name: str):
        bucket = self.client.bucket(bucket_name)
        blob = bucket.blob(blob_name)

        # Generamos la URL firmada (V4)
        url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=15), # URL temporal por seguridad
            method="GET",
            # CLAVE: Esto fuerza al navegador a descargar el archivo
            response_disposition=f"attachment; filename={blob_name}"
        )
        return url
    
    async def list_leathers(self):
        try:
            client = storage.Client()
            bucket_name = "leather_bucket"
            bucket = client.bucket(bucket_name)
            
            blobs = bucket.list_blobs()
            materials_list = []
            
            for blob in blobs:
                if blob.name.lower().endswith(('.png', '.jpg', '.jpeg')):
                    blob.reload() 
                    metadata = blob.metadata or {}
                    
                    public_url = f"https://storage.googleapis.com/{bucket_name}/{blob.name}"
                    
                    materials_list.append({
                        "id": metadata.get("id", blob.name.split('.')[0]),
                        "name": metadata.get("name", "Material sin nombre"),
                        "image": public_url, 
                    })
            
            return materials_list
        except Exception as e:
            print(f"Error: {e}")
            raise HTTPException(status_code=500, detail="Error al acceder al bucket")