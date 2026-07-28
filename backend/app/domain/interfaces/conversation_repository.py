"""Persistence ports for authenticated coaching conversations."""

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from app.domain.entities.message import Message, MessageRole
from app.domain.entities.session import CoachingSession, ConversationSummary


class ConversationRepositoryError(RuntimeError):
    """Raised when a persistence adapter cannot complete an operation."""


class ConversationSessionRepository(ABC):
    """Domain-owned contract for creating and resolving user sessions."""

    @abstractmethod
    async def create(self, user_id: UUID, title: str | None) -> CoachingSession:
        """Create a coaching session owned by ``user_id``."""

    @abstractmethod
    async def get_owned(
        self, session_id: UUID, user_id: UUID
    ) -> CoachingSession | None:
        """Return a session only when it belongs to ``user_id``."""

    @abstractmethod
    async def list_for_user(
        self, user_id: UUID, limit: int = 50
    ) -> list[ConversationSummary]:
        """List the user's most recently updated sessions."""

    @abstractmethod
    async def delete_owned(self, session_id: UUID, user_id: UUID) -> bool:
        """Delete the owned session and report whether it existed."""


class MessageRepository(ABC):
    """Domain-owned contract for message persistence and recent history."""

    @abstractmethod
    async def add(
        self,
        session_id: UUID,
        role: MessageRole,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> Message:
        """Persist one message and return its domain representation."""

    @abstractmethod
    async def list_recent(
        self,
        session_id: UUID,
        limit: int,
        *,
        exclude_message_id: UUID | None = None,
    ) -> list[Message]:
        """Return up to ``limit`` messages in chronological order."""

    @abstractmethod
    async def list_for_session(self, session_id: UUID) -> list[Message]:
        """Return all messages for a verified session in chronological order."""
