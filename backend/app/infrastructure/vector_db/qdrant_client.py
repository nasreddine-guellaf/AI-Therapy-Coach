"""Qdrant vector-store adapter skeleton.

The adapter is configurable but intentionally performs no network calls yet.
"""

from typing import Any, Sequence

from app.core.config import settings
from app.domain.interfaces.vector_store import VectorSearchResult, VectorStore


class QdrantVectorStore(VectorStore):
    """Future Qdrant implementation of the provider-neutral vector-store port."""

    def __init__(
        self,
        url: str | None = None,
        api_key: str | None = None,
        collection_name: str = "therapy_knowledge",
    ) -> None:
        self.url = url or settings.qdrant_url
        self.api_key = api_key or settings.qdrant_api_key
        self.collection_name = collection_name

        # TODO: initialize AsyncQdrantClient only when qdrant-client is added.
        # Never log api_key or vector payloads containing sensitive data.

    async def upsert(
        self,
        ids: Sequence[str],
        vectors: Sequence[Sequence[float]],
        payloads: Sequence[dict[str, Any]],
    ) -> None:
        if not (len(ids) == len(vectors) == len(payloads)):
            raise ValueError("ids, vectors, and payloads must have equal lengths")
        raise NotImplementedError("Qdrant network calls are not enabled")

    async def search(
        self, vector: Sequence[float], limit: int = 5
    ) -> list[VectorSearchResult]:
        if not vector:
            raise ValueError("query vector cannot be empty")
        if limit <= 0:
            raise ValueError("limit must be greater than zero")
        # TODO: add collection creation, payload indexes, tenant filters,
        # timeouts, retries, and score-threshold configuration.
        raise NotImplementedError("Qdrant network calls are not enabled")
