"""Qdrant adapter for the fixed, globally shared knowledge base."""

import asyncio
from collections.abc import Sequence
from typing import Any

from qdrant_client import AsyncQdrantClient, models

from app.core.config import settings
from app.domain.interfaces.vector_store import VectorSearchResult, VectorStore


class QdrantVectorStore(VectorStore):
    VECTOR_SIZE = 384

    def __init__(
        self,
        url: str | None = None,
        api_key: str | None = None,
        collection_name: str | None = None,
        client: AsyncQdrantClient | None = None,
    ) -> None:
        self.collection_name = collection_name or settings.rag_collection_name
        self._client = client or AsyncQdrantClient(
            url=url or settings.qdrant_url,
            api_key=api_key or settings.qdrant_api_key,
            timeout=10,
        )
        self._ready = False
        self._ready_lock = asyncio.Lock()

    async def upsert(
        self,
        ids: Sequence[str],
        vectors: Sequence[Sequence[float]],
        payloads: Sequence[dict[str, Any]],
    ) -> None:
        if not (len(ids) == len(vectors) == len(payloads)):
            raise ValueError("ids, vectors, and payloads must have equal lengths")
        if any(len(vector) != self.VECTOR_SIZE for vector in vectors):
            raise ValueError("Qdrant vectors must have 384 dimensions")
        await self._ensure_collection()
        await self._client.upsert(
            collection_name=self.collection_name,
            points=[
                models.PointStruct(id=id_, vector=list(vector), payload=payload)
                for id_, vector, payload in zip(ids, vectors, payloads, strict=True)
            ],
            wait=True,
        )

    async def search(
        self, vector: Sequence[float], limit: int = 5
    ) -> list[VectorSearchResult]:
        if len(vector) != self.VECTOR_SIZE:
            raise ValueError("Qdrant query vectors must have 384 dimensions")
        if limit <= 0:
            raise ValueError("limit must be greater than zero")
        await self._ensure_collection()
        response = await self._client.query_points(
            collection_name=self.collection_name,
            query=list(vector),
            limit=limit,
            with_payload=True,
        )
        return [
            VectorSearchResult(
                id=str(point.id),
                score=float(point.score),
                payload=dict(point.payload or {}),
            )
            for point in response.points
        ]

    async def delete_document(self, document_id: str) -> None:
        """Remove old chunks before replacing one fixed source document."""
        await self._ensure_collection()
        await self._client.delete(
            collection_name=self.collection_name,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="document_id",
                            match=models.MatchValue(value=document_id),
                        )
                    ]
                )
            ),
            wait=True,
        )

    async def _ensure_collection(self) -> None:
        if self._ready:
            return
        async with self._ready_lock:
            if self._ready:
                return
            if not await self._client.collection_exists(self.collection_name):
                await self._client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=self.VECTOR_SIZE,
                        distance=models.Distance.COSINE,
                    ),
                )
                await self._client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name="document_id",
                    field_schema=models.PayloadSchemaType.KEYWORD,
                    wait=True,
                )
            self._ready = True
