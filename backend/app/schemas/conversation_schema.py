from pydantic import BaseModel, Field

class ConversationRequest(BaseModel):
    message: str = Field(min_length=1, max_length=5000)
    session_id: str | None = None

class ConversationResponse(BaseModel):
    message: str
    status: str
