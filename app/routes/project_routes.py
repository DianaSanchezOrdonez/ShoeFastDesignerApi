from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from app.services.project_services import ProjectService
from app.services.auth_services import AuthService

project_service = ProjectService()
auth_service = AuthService()

router = APIRouter(
    prefix="/projects",
    tags=["Projects"],
    redirect_slashes=False,
    dependencies=[Depends(auth_service.verify_token)]
)

@router.post("/", dependencies=[Depends(auth_service.verify_token)])
async def create_project(
    name: str = Form(...),
    file: UploadFile = File(...),
    user = Depends(auth_service.verify_token)
):
    try:
        sketch_bytes = await file.read()
        project = await project_service.create_project(
            user_id=user['uid'],
            name=name,
            sketch_bytes=sketch_bytes,
            content_type=file.content_type
        )
        return project
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al crear proyecto: {str(e)}")

@router.get("/", dependencies=[Depends(auth_service.verify_token)])
async def list_projects(user = Depends(auth_service.verify_token)):
    try:
        return await project_service.get_user_projects(user['uid'])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al listar proyectos: {str(e)}")