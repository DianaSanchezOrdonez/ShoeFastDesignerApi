from fastapi import APIRouter, UploadFile, File, HTTPException, Response, Depends
from app.services.image_generation_services import ImageGenerationService
from app.services.auth_services import AuthService

gen_service = ImageGenerationService()
auth_service = AuthService()

router = APIRouter(
    prefix="/sketch-to-image", 
    tags=["Image Generation"], 
    dependencies=[Depends(auth_service.verify_token)]
)

@router.post("/shoe")
async def generate_shoe_image(file: UploadFile = File(...), user = Depends(auth_service.verify_token)):    
    
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="El archivo debe ser una imagen")

    try:
        # 1. Leer bytes del archivo subido
        input_image_bytes = await file.read()
        
        # 2. Prompt base (podrías recibirlo también por el body si quisieras)        
        prompt_text = "Convierte el boceto a una imagen realista. Fondo blanco. Un solo zapato. Cuero. Crea tres vistas: 3/4, frontal y sagital en la misma image. Relación de aspecto 3:1"

        # 3. Llamar al servicio
        generated_image_bytes = await gen_service.generate_from_sketch(
            user_id=user['uid'],
            image_bytes=input_image_bytes,
            prompt=prompt_text
        )

        if not generated_image_bytes:
            raise HTTPException(status_code=500, detail="No se pudo generar la imagen")

        return Response(content=generated_image_bytes, media_type="image/png")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))