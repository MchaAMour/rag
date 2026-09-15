from fastapi import APIRouter, File, UploadFile
from controllers import DataController



data_router = APIRouter(
    prefix="/api/v1/data",
    tags=["api_v1","Data"]
)


@data_router.post("/upload/{project_id}")
async def upload_file(project_id: str, file: UploadFile = File(...)):
    validation = DataController().validate_file(file=file)
    if isinstance(validation, tuple):
        is_valid, validation_message = validation
    else:
        is_valid, validation_message = validation, None

    return {
        "message": f"File uploaded successfully for project {project_id}.",
        "file_name": file.filename,
        "file_size": file.size,
        "is_valid": is_valid,
        "validation_message": validation_message,
    }