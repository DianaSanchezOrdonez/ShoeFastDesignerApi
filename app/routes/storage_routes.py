from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.services.image_storage_services import ImageStorageService
import uuid
from datetime import datetime

router = APIRouter(prefix="/storage", tags=["Storage"])
save_service = ImageStorageService()

@router.post("/save")
async def save_to_cloud_storage(
    file: UploadFile = File(...)
):
    try:
        # 1. Leemos los bytes del archivo que envió el frontend
        image_bytes = await file.read()
        
        # 2. Generamos un nombre de destino
        filename = f"library/shoe_{uuid.uuid4().hex}.png"
        
        # 3. LLAMAMOS AL SERVICIO (Aquí es donde ocurre la subida física)
        # Ahora save_image te devolverá la Signed URL (privada y segura)
        signed_url = save_service.save_image(
            image_bytes=image_bytes,
            destination_blob_name=filename
        )

        return {
            "status": "success",
            "url": signed_url, # Esta URL se la das al frontend para que la muestre
            "filename": filename
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/list")
async def list_my_designs():
    try:
        images = save_service.list_images()
        return {
            "status": "success",
            "count": len(images),
            "designs": images
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))