"""Provider-neutral document entities used by RAG ingestion."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from uuid import UUID, uuid4


class DocumentStatus(StrEnum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"


@dataclass(slots=True)
class Document:
    filename: str
    user_id: UUID
    content_type: str = "application/pdf"
    checksum: str | None = None
    status: DocumentStatus = DocumentStatus.UPLOADED
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
