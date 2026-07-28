from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

@dataclass(slots=True)
class CoachingSession:
    user_id: UUID
    title: str | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True, slots=True)
class ConversationSummary:
    """Owner-scoped session metadata used by conversation history listings."""

    session_id: UUID
    title: str | None
    created_at: datetime
    updated_at: datetime
    last_message_preview: str | None = None
