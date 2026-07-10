from pydantic import BaseModel, Field

class TranscriptionResponse(BaseModel):
    text: str
    status: str

class SynthesisRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)

class SynthesisResponse(BaseModel):
    audio_url: str | None
    status: str
