from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.services.auth_services import AuthService
from app.schemas.auth_schemas import LoginSchema

router = APIRouter(
    prefix="/auth", 
    tags=["Auth"]
)

auth_service = AuthService()

@router.post("/login")
async def login(data: LoginSchema):
    result = auth_service.login_user(data.email, data.password)
    
    return {
        "status": "success",
        "idToken": result["idToken"],
        "email": result["email"],
        "uid": result["localId"]
    }
    
@router.post("/logout")
async def logout(user = Depends(auth_service.verify_token)):
    try:
        # Esto invalida todos los tokens de refresco del usuario
        # La próxima vez que intente renovar sesión, Firebase lo rechazará
        auth.revoke_refresh_tokens(user['uid'])
        return {"status": "success", "message": "Tokens revocados correctamente"}
    except Exception as e:
        return {"status": "error", "message": str(e)}