"""Embedding provider port used by RAG infrastructure services."""

from abc import ABC, abstractmethod
from collections.abc import Sequence


class EmbeddingProvider(ABC):
    @abstractmethod
    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed document chunks in input order."""

    @abstractmethod
    async def embed_query(self, query: str) -> list[float]:
        """Embed one retrieval query in the same vector space."""
