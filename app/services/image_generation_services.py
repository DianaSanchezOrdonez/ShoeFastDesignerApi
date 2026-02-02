from google import genai
from google.genai import types
from app.core.config import settings
from upstash_redis.asyncio import Redis
from datetime import datetime
from fastapi import HTTPException
from uuid import uuid4
from google.cloud import storage, firestore, pubsub_v1
from base64 import b64encode
import json

aspect_ratio = "21:9" # "1:1","2:3","3:2","3:4","4:3","4:5","5:4","9:16","16:9","21:9"
resolution = "1K" # "1K", "2K", "4K"

db = firestore.Client()
storage_client = storage.Client()
bucket = storage_client.bucket("tu-bucket-shoes")

class ImageGenerationService:
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model = settings.MODEL_NANO_PRO
        # self.model = "gemini-2.5-flash-image"
        
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
        project_id: str,
        image_bytes: bytes,
        material_bytes: bytes | None = None,
        material_id: str | None = None,
    ) -> bytes | None:
        
        today = datetime.now().strftime("%Y-%m-%d")
        usage_key = f"rate_limit:{user_id}:{today}"
       
        # 1. INCREMENTO ATÓMICO (Redis suma 1 y te devuelve el nuevo valor de inmediato)
        # Si la llave no existe, Redis la crea con valor 1.
        current_count = await self.redis.incr(usage_key)
        
        # 2. Si es el primer incremento del día, ponemos la expiración de 24h
        if current_count == 1:
            await self.redis.expire(usage_key, 86400)

        # 3. VERIFICACIÓN (Ahora comparamos con el valor ya incrementado)
        # Si el límite es 2, el tercer intento devolverá current_count = 3 y entrará aquí.
        print(f"[ImageGenerationService] Uso actual para {usage_key}: {current_count}")

        if current_count > self.DAILY_LIMIT:
            # Opcional: Podrías hacer un DECR si no quieres que cuente el intento fallido
            # await self.redis.decr(usage_key) 
            raise HTTPException(
                status_code=429,
                detail=f"Has alcanzado el límite de {self.DAILY_LIMIT} generaciones diarias."
            )
            
        try:
            generated_data = None
            prompt_base = "Convierte el boceto a una imagen realista. Fondo blanco. Un solo zapato. Cuero. Crea tres vistas: 3/4, frontal y sagital en la misma image. Relación de aspecto 3:1"
            
            parts = [
            types.Part(inline_data=types.Blob(mime_type="image/jpeg", data=image_bytes))
            ]

            if material_bytes:
                # Si hay material, añadimos la instrucción extra y la segunda imagen
                prompt_text = f"{prompt_base} Usa la segunda imagen como referencia para el color y textura del cuero."
                parts.append(types.Part(inline_data=types.Blob(mime_type="image/jpeg", data=material_bytes)))
            else:
                prompt_text = prompt_base

            # Añadimos el texto al final de las partes
            parts.insert(0, types.Part(text=prompt_text))
            
            # 4. Llamada al modelo de IA
            response = self.client.models.generate_content(
                model=self.model,
                contents=[types.Content(parts=parts)],
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
                    generated_data = part.inline_data.data
                    break
                    # return part.inline_data.data

            if generated_data:
                # MANDAR A SEGUNDO PLANO
                self._publish_save_event(
                    user_id=user_id,
                    project_id=project_id,
                    material_id=material_id,
                    image_bytes=generated_data
                )

            return generated_data

        except Exception as exc:
            print(f"[ImageGenerationService] Error: {exc}")
            raise exc
        
    def _publish_save_event(self, user_id, project_id, material_id, image_bytes):
        try:
            message = {
                "type": "SAVE_GENERATION",  # <--- AGREGA ESTO
                "payload": {                # <--- Mete todo en un payload para consistencia
                    "user_id": user_id,
                    "project_id": project_id,
                    "material_id": material_id,
                    # Convertimos bytes a base64 string para el JSON
                    "image_base64": b64encode(image_bytes).decode("utf-8"),
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }
            }
            
            data = json.dumps(message).encode("utf-8")
            # Publicación asíncrona (no bloquea el return de la imagen)
            self.publisher.publish(self.topic_path, data)
            print(f"[PubSub] Evento enviado para proyecto {project_id}")
        except Exception as e:
            print(f"[PubSub] Error al publicar: {e}")