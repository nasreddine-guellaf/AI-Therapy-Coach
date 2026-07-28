"""Authenticated conversation history use cases."""

from dataclasses import dataclass
from uuid import UUID

from app.domain.entities.message import Message
from app.domain.entities.session import CoachingSession, ConversationSummary
from app.domain.interfaces.conversation_repository import (
    ConversationRepositoryError,
    ConversationSessionRepository,
    MessageRepository,
)


class ConversationHistoryNotFoundError(LookupError):
    """The session is missing or is not owned by the authenticated user."""


class ConversationHistoryUnavailableError(RuntimeError):
    """Conversation history storage is temporarily unavailable."""


@dataclass(frozen=True, slots=True)
class ConversationDetail:
    """An owned session and its chronologically ordered message history."""

    session: CoachingSession
    messages: list[Message]


class ConversationHistoryService:
    """Expose owner-scoped history without depending on FastAPI or SQLAlchemy."""

    def __init__(
        self,
        session_repository: ConversationSessionRepository,
        message_repository: MessageRepository,
        *,
        list_limit: int = 50,
    ) -> None:
        if list_limit <= 0:
            raise ValueError("list_limit must be greater than zero")
        self._sessions = session_repository
        self._messages = message_repository
        self._list_limit = list_limit

    async def list_conversations(self, user_id: UUID) -> list[ConversationSummary]:
        try:
            return await self._sessions.list_for_user(user_id, self._list_limit)
        except ConversationRepositoryError as error:
            raise ConversationHistoryUnavailableError from error

    async def get_conversation(
        self, session_id: UUID, user_id: UUID
    ) -> ConversationDetail:
        try:
            session = await self._sessions.get_owned(session_id, user_id)
            if session is None:
                raise ConversationHistoryNotFoundError
            messages = await self._messages.list_for_session(session.id)
            return ConversationDetail(session=session, messages=messages)
        except ConversationRepositoryError as error:
            raise ConversationHistoryUnavailableError from error

    async def delete_conversation(self, session_id: UUID, user_id: UUID) -> None:
        try:
            deleted = await self._sessions.delete_owned(session_id, user_id)
        except ConversationRepositoryError as error:
            raise ConversationHistoryUnavailableError from error
        if not deleted:
            raise ConversationHistoryNotFoundError
