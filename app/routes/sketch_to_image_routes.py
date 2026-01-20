from fastapi import APIRouter, UploadFile, File, HTTPException, Response, Depends
from app.services.image_generation_services import ImageGenerationService

router = APIRouter(prefix="/sketch-to-image", tags=["Image Generation"])
gen_service = ImageGenerationService()

@router.post("/shoe")
async def generate_shoe_image(file: UploadFile = File(...)):    
    """Recibe un boceto y devuelve la imagen generada por Gemini Nano Banana."""
    
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="El archivo debe ser una imagen")

    try:
        # 1. Leer bytes del archivo subido
        input_image_bytes = await file.read()
        
        # 2. Prompt base (podrías recibirlo también por el body si quisieras)        
        prompt_text = "Convierte el boceto a una imagen realista. Fondo blanco. Un solo zapato. Cuero. Crea tres vistas: 3/4, frontal y sagital en la misma image. Relación de aspecto 3:1"

        # 3. Llamar al servicio
        generated_image_bytes = await gen_service.generate_from_sketch(
            image_bytes=input_image_bytes,
            prompt=prompt_text
        )

        if not generated_image_bytes:
            raise HTTPException(status_code=500, detail="No se pudo generar la imagen")

        return Response(content=generated_image_bytes, media_type="image/png")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))