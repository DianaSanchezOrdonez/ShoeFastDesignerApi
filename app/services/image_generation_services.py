from google import genai
from google.genai import types
from app.core.config import settings
from upstash_redis.asyncio import Redis
from datetime import datetime
from fastapi import HTTPException
from uuid import uuid4
from google.cloud import storage, firestore, pubsub_v1
from base64 import b64encode, b64decode
import json
from openai import AsyncOpenAI

aspect_ratio = "21:9" # "1:1","2:3","3:2","3:4","4:3","4:5","5:4","9:16","16:9","21:9"
resolution = "1K" # "1K", "2K", "4K"

class ImageGenerationService:
    def __init__(self):
        self.gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.gemini_model = settings.MODEL_NANO_PRO
        self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.aspect_ratio = aspect_ratio
        self.resolution = resolution
        
        # Inicializamos el cliente de Upstash de forma asíncrona
        redis_url = settings.UPSTASH_REDIS_REST_URL
        redis_token = settings.UPSTASH_REDIS_REST_TOKEN
        
        print(f"[Storage] Iniciando Redis con URL: {redis_url}")
        
        self.redis = Redis(url=redis_url, token=redis_token)
        self.DAILY_LIMIT = int(settings.DAILY_LIMIT)
        
        # Cliente de Pub/Sub
        self.publisher = pubsub_v1.PublisherClient()
        # El topic path se construye con el ID de tu proyecto y el nombre del tópico
        self.topic_path = self.publisher.topic_path(
            settings.PROJECT_ID, 
            settings.PUBSUB_TOPIC_ID
        )

    async def generate_from_sketch(
        self,
        user_id: str,
        workflow_id: str,
        image_bytes: bytes,
        material_bytes: bytes | None = None,
        material_id: str | None = None,
    ) -> tuple[bytes | None, bool]:
        
        await self._check_rate_limit(user_id)
            
        try:
            if settings.ENABLE_OPENAI != "True":
                print(f"[IA] Intentando generación con Gemini ({self.gemini_model})")
                generated_data = await self._generate_with_gemini(
                    image_bytes, material_bytes, material_id
                )
                
                if generated_data:
                    self._publish_save_event(user_id, workflow_id, material_id, generated_data)
                    return generated_data, False
            
            else:
                print(f"[ImageGenerationService] Gemini saturado. Iniciando fallback multimodal con OpenAI")
                generated_data = await self._generate_with_openai_fallback(
                    image_bytes, material_id
                )
                
                if generated_data:
                    self._publish_save_event(user_id, workflow_id, material_id, generated_data)
                    return generated_data, True

        except Exception as exc:
            print(f"[ImageGenerationService] Error: {exc}")
            raise exc
        
    async def _generate_with_gemini(self, image_bytes, material_bytes, material_id):
        prompt_base = (
            "Convierte el boceto a una imagen realista de calzado profesional. "
            "Fondo blanco puro. Un solo zapato. Estilo fotográfico de catálogo. "
            "Muestra tres vistas: 3/4, lateral y frontal en la misma imagen."
        )

        parts = [types.Part(inline_data=types.Blob(mime_type="image/jpeg", data=image_bytes))]
        
        if material_bytes:
            prompt_text = f"{prompt_base} Usa la segunda imagen como referencia exacta para la textura y color del material: {material_id}."
            parts.append(types.Part(inline_data=types.Blob(mime_type="image/jpeg", data=material_bytes)))
        else:
            prompt_text = prompt_base

        parts.insert(0, types.Part(text=prompt_text))

        response = self.gemini_client.models.generate_content(
            model=self.gemini_model,
            contents=[types.Content(parts=parts)],
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(
                    aspect_ratio=self.aspect_ratio,
                    image_size=self.resolution
                ), 
            )
        )

        for part in response.parts:
            if part.inline_data and part.inline_data.data:
                return part.inline_data.data
        return None

    async def _generate_with_openai_fallback(
        self,
        image_bytes: bytes,
        material_id: str | None = None
    ) -> bytes | None:
        try:
            sketch_b64 = b64encode(image_bytes).decode("utf-8")

            analysis_response = await self.openai_client.responses.create(
                model="gpt-5.2",
                input=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "Describe la geometría física del zapato Y la apariencia visible del material.\n"
                                "Incluye obligatoriamente:\n"
                                "- silueta general y proporciones\n"
                                "- forma de la punta\n"
                                "- estructura del upper\n"
                                "- grosor de la suela y altura del talón\n"
                                "- costuras y uniones\n"
                                "- cordones o sistemas de ajuste\n"
                                "- tonos de color visibles y acabado del material (mate, brillante, texturizado, grano)\n\n"
                                "NO menciones bocetos, dibujos ni ilustraciones.\n"
                                "Redacta una descripción técnica neutra, como para fotografía de producto."
                            )
                        },
                        {
                            "type": "input_image",
                            "image_url": f"data:image/jpeg;base64,{sketch_b64}"
                        }
                    ]
                }]
            )

            technical_description = analysis_response.output_text.strip()

            if material_id:
                material_line = (
                    f"El material del zapato DEBE ser exactamente: {material_id}. "
                    "No alteres el color, tono ni acabado del material bajo ninguna circunstancia."
                )
            else:
                material_line = (
                    "Conserva exactamente el color, material y acabado descritos previamente. "
                    "No realices reinterpretaciones ni variaciones."
                )

            final_prompt = f"""
            Fotografía de producto ultra realista en estudio de un solo zapato.

            DISEÑO (debe coincidir exactamente):
            {technical_description}

            MATERIAL (CRÍTICO):
            {material_line}

            COMPOSICIÓN (ESTRICTA):
            - Un solo zapato
            - Tres vistas en la misma imagen:
            • Vista 3/4
            • Perfil lateral
            • Vista frontal
            - Distribución limpia estilo catálogo con separación clara

            ESTILO:
            - Fondo blanco puro
            - Sombras suaves y neutras de estudio
            - Fotografía de producto de alta gama
            - Sin bocetos
            - Sin dibujos
            - Sin estilo ilustrado
            """

            image_response = await self.openai_client.images.generate(
                model="gpt-image-1",
                prompt=final_prompt,
                size="1536x1024",
                quality="medium"
            )

            return b64decode(image_response.data[0].b64_json)

        except Exception as exc:
            print(f"[OpenAI Fallback Error] {exc}")
            return None
        
    def _publish_save_event(self, user_id, workflow_id, material_id, image_bytes):
        try:
            message = {
                "type": "SAVE_GENERATION", 
                "payload": {               
                    "user_id": user_id,
                    "workflow_id": workflow_id,
                    "material_id": material_id,
                    "image_base64": b64encode(image_bytes).decode("utf-8"),
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }
            }
            
            # Convertimos el mensaje a bytes para enviarlo al publisher
            data = json.dumps(message).encode("utf-8")
            
            # 1. Publicamos el mensaje
            future = self.publisher.publish(self.topic_path, data)
            
            # 2. EL CAMBIO CLAVE: Esperar el resultado
            # Esto bloquea la ejecución solo unos milisegundos hasta confirmar que Pub/Sub recibió el mensaje.
            message_id = future.result(timeout=60) 
            
            print(f"[PubSub] Evento enviado exitosamente. ID: {message_id} para flujo de trabajo {workflow_id}")
        except Exception as e:
            print(f"[PubSub] Error al publicar: {e}")
            
    async def _check_rate_limit(self, user_id):
        today = datetime.now().strftime("%Y-%m-%d")
        usage_key = f"rate_limit:{user_id}:{today}"
        
        current_count = await self.redis.incr(usage_key)
        if current_count == 1:
            await self.redis.expire(usage_key, 86400)
        
        print(f"[ImageGenerationService] Uso actual para {usage_key}: {current_count}")

        if current_count > self.DAILY_LIMIT:
            raise HTTPException(
                status_code=429,
                detail=f"Límite diario de {self.DAILY_LIMIT} generaciones alcanzado."
            )