from fastapi import APIRouter, File, UploadFile, status
from app.schemas.voice_schema import SynthesisRequest, SynthesisResponse, TranscriptionResponse

router = APIRouter(prefix="/voice", tags=["voice"])

@router.post("/transcribe", response_model=TranscriptionResponse, status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def transcribe(audio: UploadFile = File(...)) -> TranscriptionResponse:
    return TranscriptionResponse(text="", status="not_implemented")

@router.post("/synthesize", response_model=SynthesisResponse, status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def synthesize(request: SynthesisRequest) -> SynthesisResponse:
    return SynthesisResponse(audio_url=None, status="not_implemented")
