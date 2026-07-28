"""HTTP schemas for authenticated conversation history."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.entities.message import Message
from app.domain.entities.session import CoachingSession, ConversationSummary


class ConversationSummaryResponse(BaseModel):
    session_id: UUID
    title: str | None
    created_at: datetime
    updated_at: datetime
    last_message_preview: str | None

    @classmethod
    def from_domain(
        cls, summary: ConversationSummary
    ) -> "ConversationSummaryResponse":
        return cls(
            session_id=summary.session_id,
            title=summary.title,
            created_at=summary.created_at,
            updated_at=summary.updated_at,
            last_message_preview=summary.last_message_preview,
        )


class ConversationMessageResponse(BaseModel):
    id: UUID
    role: str
    content: str
    metadata: dict[str, Any] | None = None
    created_at: datetime

    @classmethod
    def from_domain(cls, message: Message) -> "ConversationMessageResponse":
        return cls(
            id=message.id,
            role=message.role.value,
            content=message.content,
            metadata=message.metadata,
            created_at=message.created_at,
        )


class ConversationDetailResponse(BaseModel):
    session_id: UUID
    title: str | None
    created_at: datetime
    updated_at: datetime
    messages: list[ConversationMessageResponse] = Field(default_factory=list)

    @classmethod
    def from_domain(
        cls, session: CoachingSession, messages: list[Message]
    ) -> "ConversationDetailResponse":
        return cls(
            session_id=session.id,
            title=session.title,
            created_at=session.created_at,
            updated_at=session.updated_at,
            messages=[ConversationMessageResponse.from_domain(item) for item in messages],
        )
