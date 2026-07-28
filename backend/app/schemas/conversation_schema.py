from pydantic import BaseModel, Field
from uuid import UUID


class ConversationRequest(BaseModel):
    message: str = Field(min_length=1, max_length=5000)
    session_id: UUID | None = None


class ConversationResponse(BaseModel):
    message: str
    status: str
    session_id: UUID | None = None
    memory_items_used: int = 0
    rag_chunks_used: int = 0
    source_ids: list[str] = Field(default_factory=list)
