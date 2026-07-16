"""HTTP adapter for the conversation use case."""

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_conversation_manager
from app.domain.services.conversation_manager import (
    ConversationCommand,
    ConversationManager,
)
from app.schemas.conversation_schema import ConversationRequest, ConversationResponse


router = APIRouter(prefix="/conversation", tags=["conversation"])


@router.post(
    "/message",
    response_model=ConversationResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def send_message(
    request: ConversationRequest,
    manager: ConversationManager = Depends(get_conversation_manager),
) -> ConversationResponse:
    """Translate HTTP input into a domain command and map its result back."""
    result = await manager.handle(
        ConversationCommand(
            message=request.message,
            session_id=request.session_id,
        )
    )
    return ConversationResponse(
        message=result.message,
        status=result.status,
        memory_items_used=result.memory_items_used,
        rag_chunks_used=result.rag_chunks_used,
        source_ids=result.source_ids,
    )
