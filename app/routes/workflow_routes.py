from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from app.services.workflow_services import WorkflowService
from app.services.auth_services import AuthService

workflow_service = WorkflowService()
auth_service = AuthService()

router = APIRouter(
    prefix="/workflows",
    tags=["Workflows"],
    redirect_slashes=False,
    dependencies=[Depends(auth_service.verify_token)]
)

@router.post("/", dependencies=[Depends(auth_service.verify_token)])
async def create_workflow(
    name: str = Form(...),
    file: UploadFile = File(...),
    user = Depends(auth_service.verify_token)
):
    try:
        sketch_bytes = await file.read()
        workflow = await workflow_service.create_workflow(
            user_id=user['uid'],
            name=name,
            sketch_bytes=sketch_bytes,
            content_type=file.content_type
        )
        return workflow
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al crear flujo de trabajo: {str(e)}")

@router.get("/", dependencies=[Depends(auth_service.verify_token)])
async def list_workflows(user = Depends(auth_service.verify_token)):
    try:
        return await workflow_service.get_user_workflows(user['uid'])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al listar flujos de trabajo: {str(e)}")

@router.get("/latest-generation")
async def list_workflows_with_latest_generation(
    user = Depends(auth_service.verify_token),
):
    workflows_with_latest_generation = await workflow_service.get_workflows_with_latest_generation(user_id=user['uid'])

    return workflows_with_latest_generation

@router.get("/generate-download-url/{blob_path:path}")
async def get_download_link(blob_path: str):
    return workflow_service.generate_download_url(blob_path)
       
@router.get("/{workflow_id}")
async def get_workflow_details(
    workflow_id: str, 
    user = Depends(auth_service.verify_token)
):
    details = await workflow_service.get_workflow_details(workflow_id, user["uid"])
    
    if not details:
        raise HTTPException(
            status_code=404, 
            detail="Flujo de trabajo no encontrado"
        )
    
    return details

@router.patch("/{workflow_id}/close")
async def close_workflow(
    workflow_id: str,
    user = Depends(auth_service.verify_token)
):    
    try:
        updated_data = await workflow_service.close_workflow(
            workflow_id=workflow_id, 
            user_id=user["uid"]
        )

        if not updated_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow no encontrado o no pertenece al usuario"
            )

        return {
            "status": "success",
            "message": "Workflow cerrado exitosamente",
            "data": updated_data
        }

    except Exception as e:
        print(f"[API Error Close Workflow] {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno al cerrar el flujo"
        )