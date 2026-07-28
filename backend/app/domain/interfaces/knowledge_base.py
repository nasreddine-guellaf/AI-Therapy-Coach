"""Provider-neutral contracts for the fixed internal knowledge base."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


class KnowledgeBaseError(RuntimeError):
    """Base class for safe knowledge-base ingestion failures."""


class KnowledgeBaseConfigurationError(KnowledgeBaseError):
    """The configured knowledge-base directory or file set is invalid."""


class DocumentValidationError(ValueError):
    """A trusted PDF cannot be processed by the supported text extractor."""


class NoExtractableTextError(DocumentValidationError):
    """A PDF contains no text layer and OCR is intentionally unsupported."""


class DocumentIndexingError(KnowledgeBaseError):
    """Extraction, embedding, or vector indexing failed internally."""


@dataclass(frozen=True, slots=True)
class KnowledgeBaseDocument:
    """Metadata for one owner-managed source file."""

    document_id: str
    filename: str
    created_at: datetime


class KnowledgeBaseIndexer(ABC):
    """Port for indexing one trusted fixed-knowledge document."""

    @abstractmethod
    async def index(self, document: KnowledgeBaseDocument, content: bytes) -> int:
        """Replace the document's vector chunks and return their count."""

