# Usamos una imagen ligera de Python
FROM python:3.11-slim

# Evita que Python genere archivos .pyc y permite logs en tiempo real
ENV PYTHONUNBUFFERED True

# Directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiamos primero el archivo de requerimientos para aprovechar la caché de Docker
COPY requirements.txt .

# Instalamos las dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos todo el código del proyecto (main.py y la carpeta app/)
COPY . .

# Cloud Run inyecta automáticamente la variable de entorno PORT (normalmente 8080)
# Usamos la variable $PORT para que Google pueda gestionar el tráfico
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}