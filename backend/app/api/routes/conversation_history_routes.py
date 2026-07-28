"""Thin HTTP adapter for authenticated conversation history."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.auth_dependencies import get_current_user
from app.api.dependencies import get_conversation_history_service
from app.domain.entities.user import User
from app.domain.services.conversation_history_service import (
    ConversationHistoryNotFoundError,
    ConversationHistoryService,
    ConversationHistoryUnavailableError,
)
from app.schemas.conversation_history_schema import (
    ConversationDetailResponse,
    ConversationSummaryResponse,
)


router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationSummaryResponse])
async def list_conversations(
    service: Annotated[
        ConversationHistoryService, Depends(get_conversation_history_service)
    ],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[ConversationSummaryResponse]:
    try:
        conversations = await service.list_conversations(current_user.id)
    except ConversationHistoryUnavailableError as error:
        raise _storage_unavailable() from error
    return [ConversationSummaryResponse.from_domain(item) for item in conversations]


@router.get("/{session_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    session_id: UUID,
    service: Annotated[
        ConversationHistoryService, Depends(get_conversation_history_service)
    ],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ConversationDetailResponse:
    try:
        conversation = await service.get_conversation(session_id, current_user.id)
    except ConversationHistoryNotFoundError as error:
        raise _not_found() from error
    except ConversationHistoryUnavailableError as error:
        raise _storage_unavailable() from error
    return ConversationDetailResponse.from_domain(
        conversation.session, conversation.messages
    )


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    session_id: UUID,
    service: Annotated[
        ConversationHistoryService, Depends(get_conversation_history_service)
    ],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    try:
        await service.delete_conversation(session_id, current_user.id)
    except ConversationHistoryNotFoundError as error:
        raise _not_found() from error
    except ConversationHistoryUnavailableError as error:
        raise _storage_unavailable() from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Conversation session not found",
    )


def _storage_unavailable() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Conversation storage is temporarily unavailable",
    )
