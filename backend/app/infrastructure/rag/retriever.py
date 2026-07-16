"""Provider-neutral retrieval orchestration service."""

from dataclasses import dataclass, field
from typing import Any

from app.domain.interfaces.vector_store import VectorStore
from app.infrastructure.rag.embeddings import EmbeddingProvider


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    """A relevant text chunk ready for prompt construction."""

    id: str
    text: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


class Retriever:
    """Embed a query and retrieve matching chunks through injected ports."""

    def __init__(
        self, embedding_provider: EmbeddingProvider, vector_store: VectorStore
    ) -> None:
        self.embedding_provider = embedding_provider
        self.vector_store = vector_store

    async def retrieve_relevant_chunks(
        self, query: str, top_k: int = 5
    ) -> list[RetrievedChunk]:
        """Return up to ``top_k`` relevant chunks without provider coupling."""
        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("query cannot be empty")
        if top_k <= 0:
            raise ValueError("top_k must be greater than zero")

        query_vector = await self.embedding_provider.embed_query(normalized_query)
        results = await self.vector_store.search(query_vector, limit=top_k)

        chunks: list[RetrievedChunk] = []
        for result in results:
            payload = dict(result.payload)
            text = payload.pop("text", None)
            if not isinstance(text, str) or not text.strip():
                continue
            chunks.append(
                RetrievedChunk(
                    id=result.id,
                    text=text,
                    score=result.score,
                    metadata=payload,
                )
            )

        # TODO: add score thresholds, authorization filters, deduplication,
        # reranking, citation validation, and retrieval telemetry.
        return chunks
