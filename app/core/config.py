# app/core/config.py
import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Google Cloud & API Keys
    PROJECT_ID: str
    LOCATION: str = "us-central1"
    GEMINI_API_KEY: str
    GOOGLE_APPLICATION_CREDENTIALS: str
    
    # Modelos Nano Banana
    MODEL_NANO_PRO: str
    MODEL_NANO_FAST: str
    MODEL_GEMINI_TEXT: str
    
    # Auth Firebase
    FIREBASE_WEB_API_KEY: str

    # Configuración de la API
    API_TITLE: str = "Shoe Design API"
    API_V1_STR: str = "/api/v1"
    
    # Configuración Google Cloud Storage
    GCS_BUCKET_NAME: str
    
    # Upstash Redis
    UPSTASH_REDIS_REST_URL: str
    UPSTASH_REDIS_REST_TOKEN: str
    DAILY_LIMIT: str
    
    PUBSUB_TOPIC_ID: str
    
    OPENAI_API_KEY: str

    # Cargar archivo .env
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

# Instancia global para ser usada en toda la app
settings = Settings()

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = settings.GOOGLE_APPLICATION_CREDENTIALS