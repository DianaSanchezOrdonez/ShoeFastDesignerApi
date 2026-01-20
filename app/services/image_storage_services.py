from google.cloud import storage
from google.oauth2 import service_account
from google.api_core.exceptions import GoogleAPIError
from app.core.config import settings
from datetime import timedelta

class ImageStorageService:
    def __init__(self):
        # creds = service_account.Credentials.from_service_account_file(
        #     settings.GOOGLE_APPLICATION_CREDENTIALS
        # )
        
        self.client = storage.Client(
            # credentials=creds, 
            project=settings.PROJECT_ID
        )
        self.bucket_name = settings.GCS_BUCKET_NAME
        
    def save_image(self, image_bytes: bytes, destination_blob_name: str, content_type: str = "image/png") -> str:
        try:
            bucket = self.client.bucket(self.bucket_name)
            blob = bucket.blob(destination_blob_name)
            blob.upload_from_string(image_bytes, content_type=content_type)
            
            print(f"[ImageStorageService] Imagen guardada: {destination_blob_name}")

            return f"gs://{self.bucket_name}/{destination_blob_name}"
        
        except GoogleAPIError as e:
            print(f"[ImageStorageService] Error de Google Cloud: {e}")
            raise
        except Exception as e:
            print(f"[ImageStorageService] Error inesperado: {e}")
            raise
          
    def list_images(self, prefix: str = "library/"):
        try:
            bucket = self.client.bucket(self.bucket_name)
            # prefix="library/" sirve para no traer archivos de otras carpetas si las tuvieras
            blobs = bucket.list_blobs(prefix=prefix)
            
            image_list = []
            for blob in blobs:
                # Ignorar si es una carpeta vacía
                if blob.name.endswith('/'):
                    continue
                
                # Generamos una URL firmada para que el frontend pueda verla
                url = blob.generate_signed_url(
                    version="v4",
                    expiration=timedelta(minutes=60), # 1 hora de visibilidad
                    method="GET",
                )
                
                image_list.append({
                    "name": blob.name.replace(prefix, ""), # Nombre limpio
                    "url": url,
                    "updated": blob.updated
                })
            
            # Ordenar por fecha de creación (más recientes primero)
            image_list.sort(key=lambda x: x['updated'], reverse=True)
            
            return image_list
        except Exception as e:
            print(f"[ImageStorageService] Error al listar: {e}")
            raise