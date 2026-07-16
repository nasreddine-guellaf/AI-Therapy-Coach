"""Embedding provider contract plus a deterministic local test double."""

from abc import ABC, abstractmethod
import hashlib
from typing import Sequence


class EmbeddingProvider(ABC):
    """Port implemented later by OpenAI or another embedding provider."""

    @abstractmethod
    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed document chunks in input order."""
        raise NotImplementedError

    @abstractmethod
    async def embed_query(self, query: str) -> list[float]:
        """Embed one retrieval query in the same vector space."""
        raise NotImplementedError


class DeterministicMockEmbeddingProvider(EmbeddingProvider):
    """Non-semantic embeddings for local tests; never use for real retrieval."""

    def __init__(self, dimensions: int = 8) -> None:
        if dimensions <= 0:
            raise ValueError("dimensions must be greater than zero")
        self.dimensions = dimensions

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    async def embed_query(self, query: str) -> list[float]:
        if not query.strip():
            raise ValueError("query cannot be empty")
        return self._embed(query)

    def _embed(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        return [
            (digest[index % len(digest)] / 127.5) - 1.0
            for index in range(self.dimensions)
        ]


# TODO: add an OpenAIEmbeddingProvider adapter with batching, retry/backoff,
# dimension validation, observability, and strict secret redaction.
