"""Domain port for retrieval-augmented context lookup."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    """Provider-neutral chunk returned to conversation orchestration."""

    id: str
    text: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def source_id(self) -> str:
        return str(self.metadata.get("source_id", self.id))

    @property
    def filename(self) -> str:
        return str(self.metadata.get("filename", "document.pdf"))

    @property
    def page_number(self) -> int | None:
        value = self.metadata.get("page_number")
        return value if isinstance(value, int) else None

    @property
    def chunk_index(self) -> int | None:
        value = self.metadata.get("chunk_index")
        return value if isinstance(value, int) else None


class ChunkRetriever(ABC):
    """Port for retrieving relevant knowledge without exposing vector details."""

    @abstractmethod
    async def retrieve_relevant_chunks(
        self, query: str, top_k: int = 5
    ) -> list[RetrievedChunk]:
        """Return relevant chunks from the fixed internal knowledge base."""
        raise NotImplementedError


class RetrievalUnavailableError(RuntimeError):
    """Retrieval infrastructure is unavailable; callers may use empty context."""
