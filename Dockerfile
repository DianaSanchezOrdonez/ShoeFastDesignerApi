# Usamos la imagen oficial de Python 3.12 (versión ligera)
FROM python:3.12-slim

# Evita que Python genere archivos .pyc y permite ver logs en tiempo real
ENV PYTHONUNBUFFERED=1
ENV APP_HOME=/app

WORKDIR $APP_HOME

# Instalamos dependencias del sistema necesarias para algunas librerías de Google
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copiamos e instalamos los requerimientos
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiamos el resto del código
COPY . .

# Comando de inicio usando la variable de entorno PORT que asigna Cloud Run
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}