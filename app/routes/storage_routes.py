from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from app.services.image_storage_services import ImageStorageService
from app.services.auth_services import AuthService
import uuid
from datetime import datetime
from app.schemas.storage_schemas import BucketCreate, MoveImagesRequest

storage_service = ImageStorageService()
auth_service = AuthService()

router = APIRouter(
    prefix="/storage", 
    tags=["Storage"],
    dependencies=[Depends(auth_service.verify_token)]
)

@router.post("/save")
async def save_to_cloud_storage(
    file: UploadFile = File(...),
    folder: str = None,
    user = Depends(auth_service.verify_token)
):
    try:
        # 1. Aseguramos que el usuario tenga su propio bucket
        # user_bucket = storage_service.get_or_create_user_bucket(user['uid'])
        
        # 2. Procesamos la imagen
        image_bytes = await file.read()
        # Ya no necesitamos el prefijo 'library/' si el bucket es solo suyo
        filename = f"shoe_{uuid.uuid4().hex}.png"
        
        # 3. Guardamos en SU bucket personal
        signed_url = storage_service.save_image(
            user_uid=user['uid'],
            image_bytes=image_bytes,
            filename=filename,
            folder=folder,
        )

        return {
            "status": "success",
            "url": signed_url,
            # "bucket": user_bucket,
            "filename": filename
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/list")
async def list_my_designs(user = Depends(auth_service.verify_token)):
    try:
        # 1. Obtenemos el nombre del bucket del usuario
        user_bucket = storage_service.get_or_create_user_bucket(user['uid'])
        
        # 2. Listamos de ese bucket (prefix=None porque están en la raíz)
        images = storage_service.list_images(user_uid=user['uid'], prefix=None)
        
        return {
            "status": "success",
            "bucket_id": user_bucket,
            "designs": images
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create-bucket")
async def create_new_collection(
    data: BucketCreate,
    user = Depends(auth_service.verify_token)
):
    try:
        main_bucket_name = storage_service.get_or_create_user_bucket(user['uid'])
        bucket = storage_service.client.bucket(main_bucket_name)
        
        folder_name = data.collection_name.lower().replace(' ', '-')
        
        placeholder_blob = bucket.blob(f"{folder_name}/.keep")
        placeholder_blob.upload_from_string("")
        
        return {
            "status": "success",
            "message": "Colección creada",
            "folder_name": folder_name
        }
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/move-images")
async def move_images_to_bucket(data: MoveImagesRequest):
    try:
        success_count = 0
        for blob_name in data.image_names:
            success = storage_service.move_blob(blob_name, data.target_bucket_name)
            if success:
                success_count += 1
        
        return {
            "status": "success",
            "message": f"Se movieron {success_count} imágenes exitosamente.",
            "target": data.target_bucket_name
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fallo al mover archivos: {str(e)}")
    
@router.get("/collections")
async def get_my_collections(user = Depends(auth_service.verify_token)):
    try:
        user_bucket = storage_service.get_or_create_user_bucket(user['uid'])
        
        collections = storage_service.list_buckets(user_bucket)
        
        return {
            "status": "success",
            "collections": collections
        }
    except Exception as e:
        print(f"Error listing collections: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/generate-download-url/{filename}")
async def get_download_link(filename: str, user = Depends(auth_service.verify_token)):
    # El bucket depende del ID del usuario autenticado
    user_id_clean = user['uid'][:10].lower()
    user_bucket = f"sfd-user-{user_id_clean}-main"

    url = storage_service.generate_download_url(user_bucket, filename)
    return {"download_url": url}