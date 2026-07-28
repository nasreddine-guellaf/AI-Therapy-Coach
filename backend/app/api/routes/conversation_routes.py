"""HTTP adapter for the conversation use case."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.auth_dependencies import get_current_user
from app.api.dependencies import get_conversation_manager
from app.domain.entities.user import User
from app.domain.services.conversation_manager import (
    ConversationCommand,
    ConversationManager,
    ConversationPersistenceUnavailableError,
    ConversationSessionAccessError,
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
    try:
        result = await manager.handle(
            ConversationCommand(
                message=request.message,
                session_id=request.session_id,
                user_id=current_user.id,
            )
        )
    except ConversationSessionAccessError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation session not found",
        ) from error
    except ConversationPersistenceUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Conversation storage is temporarily unavailable",
        ) from error

    return ConversationResponse(
        message=result.message,
        status=result.status,
        session_id=result.session_id,
        memory_items_used=result.memory_items_used,
        rag_chunks_used=result.rag_chunks_used,
        source_ids=result.source_ids,
    )
