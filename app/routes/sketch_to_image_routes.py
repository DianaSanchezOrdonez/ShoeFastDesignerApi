from fastapi import APIRouter, UploadFile, File, HTTPException, Response, Depends, Form
from app.services.image_generation_services import ImageGenerationService
from app.services.auth_services import AuthService
import httpx

gen_service = ImageGenerationService()
auth_service = AuthService()

router = APIRouter(
    prefix="/sketch-to-image", 
    tags=["Image Generation"], 
    dependencies=[Depends(auth_service.verify_token)]
)

@router.post("/shoe")
async def generate_shoe_image(
    file: UploadFile = File(...), 
    workflow_id: str = Form(...),
    # material_file: UploadFile = File(None),
    material_id: str = Form(None),
    material_url: str = Form(None),
    user = Depends(auth_service.verify_token)
    ):    
    
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="El archivo debe ser una imagen")

    try:
        # 1. Leer bytes del archivo subido
        input_image_bytes = await file.read()
        material_image_bytes = None
        
        # Si el usuario envió un material, leemos sus bytes
        # if material_file:
        #     material_image_bytes = await material_file.read()
        if material_url:
            async with httpx.AsyncClient() as client:
                resp = await client.get(material_url)
                if resp.status_code == 200:
                    material_image_bytes = resp.content
        
        # 2. Prompt base (podrías recibirlo también por el body si quisieras)        
        # prompt_text = "Convierte el boceto a una imagen realista. Fondo blanco. Un solo zapato. Cuero. Crea tres vistas: 3/4, frontal y sagital en la misma image. Relación de aspecto 3:1"

        # 3. Llamar al servicio
        generated_image_bytes, is_fallback = await gen_service.generate_from_sketch(
            user_id=user['uid'],
            workflow_id=workflow_id,
            image_bytes=input_image_bytes,
            material_bytes=material_image_bytes,
            material_id=material_id
        )

        if not generated_image_bytes:
            raise HTTPException(status_code=500, detail="No se pudo generar la imagen")
        
        # Si is_fallback es True, mandamos el header para que el frontend lo detecte
        headers = {"X-Strategy": "fallback"} if is_fallback else {"X-Strategy": "primary"}
        
        return Response(content=generated_image_bytes, media_type="image/png", headers=headers)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))