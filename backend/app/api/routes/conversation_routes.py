"""HTTP adapter for the conversation use case."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.auth_dependencies import get_current_user
from app.api.dependencies import get_conversation_manager
from app.domain.entities.user import User
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
    manager: Annotated[ConversationManager, Depends(get_conversation_manager)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ConversationResponse:
    """Translate HTTP input into a domain command and map its result back."""
    result = await manager.handle(
        ConversationCommand(
            message=request.message,
            session_id=request.session_id,
            user_id=current_user.id,
        )
    )
    return ConversationResponse(
        message=result.message,
        status=result.status,
        memory_items_used=result.memory_items_used,
        rag_chunks_used=result.rag_chunks_used,
        source_ids=result.source_ids,
    )
