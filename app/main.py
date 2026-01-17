from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import sketch_to_image_routes, storage_routes

app = FastAPI(title="Shoe Design API")

# Configurar CORS (Para tu frontend en Next.js)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sketch_to_image_routes.router)
app.include_router(storage_routes.router)

@app.get("/")
async def root():
    return {"message": "Shoe Faster Design API is running"}