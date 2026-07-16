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


class ChunkRetriever(ABC):
    """Port for retrieving relevant knowledge without exposing vector details."""

    @abstractmethod
    async def retrieve_relevant_chunks(
        self, query: str, top_k: int = 5
    ) -> list[RetrievedChunk]:
        """Return relevant, authorization-filtered chunks for a user query."""
        raise NotImplementedError
