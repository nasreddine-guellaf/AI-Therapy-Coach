"""Local multilingual E5 embeddings plus a deterministic test double."""

import asyncio
import hashlib
from collections.abc import Sequence
from typing import Any

from app.domain.interfaces.embedding_provider import EmbeddingProvider


class LocalE5EmbeddingProvider(EmbeddingProvider):
    """Lazy, local sentence-transformers adapter for multilingual E5-small."""

    dimensions = 384

    def __init__(self, model_name: str = "intfloat/multilingual-e5-small") -> None:
        self.model_name = model_name
        self._model: Any | None = None
        self._load_lock = asyncio.Lock()

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        normalized = [text.strip() for text in texts]
        if not normalized or any(not text for text in normalized):
            raise ValueError("document texts cannot be empty")
        return await self._encode([f"passage: {text}" for text in normalized])

    async def embed_query(self, query: str) -> list[float]:
        normalized = query.strip()
        if not normalized:
            raise ValueError("query cannot be empty")
        return (await self._encode([f"query: {normalized}"]))[0]

    async def _encode(self, texts: Sequence[str]) -> list[list[float]]:
        model = await self._get_model()
        vectors = await asyncio.to_thread(
            model.encode,
            list(texts),
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        result = [vector.tolist() for vector in vectors]
        if any(len(vector) != self.dimensions for vector in result):
            raise RuntimeError("Embedding model returned an unexpected vector size")
        return result

    async def _get_model(self):
        if self._model is not None:
            return self._model
        async with self._load_lock:
            if self._model is None:
                from sentence_transformers import SentenceTransformer

                self._model = await asyncio.to_thread(
                    SentenceTransformer, self.model_name
                )
        return self._model


class DeterministicMockEmbeddingProvider(EmbeddingProvider):
    """Non-semantic embeddings for tests; never use for real retrieval."""

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
