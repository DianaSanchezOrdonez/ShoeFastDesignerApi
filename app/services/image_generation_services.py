from google import genai
from google.genai import types
from app.core.config import settings

aspect_ratio = "21:9" # "1:1","2:3","3:2","3:4","4:3","4:5","5:4","9:16","16:9","21:9"
resolution = "1K" # "1K", "2K", "4K"

class ImageGenerationService:
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model = settings.MODEL_NANO_PRO

    async def generate_from_sketch(
        self,
        image_bytes: bytes,
        prompt: str
    ) -> bytes | None:
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=[
                    types.Content(
                        parts=[
                            types.Part(text=prompt),
                            types.Part(
                                inline_data=types.Blob(
                                    mime_type="image/jpeg",
                                    data=image_bytes,
                                )
                            )
                        ]
                    )
                ],
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=types.ImageConfig(
                        aspect_ratio=aspect_ratio,
                        image_size=resolution
                    ), 
                )
            )
            
            # Extraemos los bytes de la imagen de la respuesta
            # for part in response.parts:
            #     if part.inline_data:
            #         # En el nuevo SDK, as_image() devuelve un objeto PIL
            #         image_pil = part.as_image()
            #         img_byte_arr = io.BytesIO()
            #         image_pil.save(img_byte_arr, format='PNG')
            #         return img_byte_arr.getvalue()

            for part in response.parts:
                if part.inline_data and part.inline_data.data:
                    return part.inline_data.data

            return None

        except Exception as exc:
            print(f"[ImageGenerationService] Error: {exc}")
            raise exc
