# app/core/config.py
import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Google Cloud & API Keys
    PROJECT_ID: str
    LOCATION: str = "us-central1"
    GEMINI_API_KEY: str
    
    # Modelos Nano Banana
    MODEL_NANO_PRO: str = "gemini-3-pro-image-preview"
    MODEL_NANO_FAST: str = "gemini-2.5-flash-image"
    MODEL_GEMINI_TEXT: str = "gemini-3-pro-preview"

    # Configuración de la API
    API_TITLE: str = "Shoe Design API"
    API_V1_STR: str = "/api/v1"
    
    # Configuración Google Cloud Storage
    GCS_BUCKET_NAME: str

    # Cargar archivo .env
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

# Instancia global para ser usada en toda la app
settings = Settings()