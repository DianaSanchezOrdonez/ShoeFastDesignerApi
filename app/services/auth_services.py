import firebase_admin
import requests
from firebase_admin import auth, credentials
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings

security = HTTPBearer()

class AuthService:
    def __init__(self):
        if not firebase_admin._apps:
            cred = credentials.Certificate(settings.GOOGLE_APPLICATION_CREDENTIALS)
            firebase_admin.initialize_app(cred)
        
        self.api_key = settings.FIREBASE_WEB_API_KEY
        self.auth_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={self.api_key}"

    def login_user(self, email: str, password: str):
        payload = {"email": email, "password": password, "returnSecureToken": True}
        response = requests.post(self.auth_url, json=payload)
        
        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="Credenciales incorrectas")
        
        return response.json()

    def verify_token(self, res: HTTPAuthorizationCredentials = Depends(security)):
        try:
            token = res.credentials
            decoded_token = auth.verify_id_token(token)
            return decoded_token
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido o expirado"
            )