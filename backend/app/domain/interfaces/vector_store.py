from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Sequence


@dataclass(frozen=True, slots=True)
class VectorSearchResult:
    """Provider-neutral result returned by vector search adapters."""

    id: str
    score: float
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class VectorStoreReadiness:
    """Safe aggregate state without vector payload or document text."""

    qdrant_reachable: bool
    collection_exists: bool
    indexed_document_count: int
    total_chunk_count: int


class VectorStore(ABC):
    @abstractmethod
    async def upsert(
        self,
        ids: Sequence[str],
        vectors: Sequence[Sequence[float]],
        payloads: Sequence[dict[str, Any]],
    ) -> None: ...

    @abstractmethod
    async def delete_document(self, document_id: str) -> None:
        """Delete all existing chunks for one stable knowledge document."""

    @abstractmethod
    async def recreate_collection(self) -> None:
        """Delete and recreate the configured collection."""

    @abstractmethod
    async def inspect_readiness(self) -> VectorStoreReadiness:
        """Return safe aggregate collection statistics."""

    @abstractmethod
    async def search(
        self, vector: Sequence[float], limit: int = 5
    ) -> list[VectorSearchResult]: ...
