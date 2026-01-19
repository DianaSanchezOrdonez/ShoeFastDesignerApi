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

@app.get("/health")
def health():
    return {"status": "ok", "message": "Service is healthy", "version": "1.0.0"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port)