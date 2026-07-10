from fastapi import APIRouter, File, UploadFile, status
from app.schemas.document_schema import DocumentUploadResponse

router = APIRouter(prefix="/documents", tags=["documents"])

@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(file: UploadFile = File(...)) -> DocumentUploadResponse:
    # TODO: validate PDF then delegate to the asynchronous ingestion pipeline.
    return DocumentUploadResponse(filename=file.filename or "document.pdf", status="pending")
