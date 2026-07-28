from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from uuid import UUID, uuid4
from typing import Any

class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"

@dataclass(slots=True)
class Message:
    session_id: UUID
    role: MessageRole
    content: str
    metadata: dict[str, Any] | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
