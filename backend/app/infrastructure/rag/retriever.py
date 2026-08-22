"""Provider-neutral retrieval orchestration adapter."""

import logging
from difflib import SequenceMatcher
from time import perf_counter

from app.domain.interfaces.embedding_provider import EmbeddingProvider
from app.domain.interfaces.retriever import (
    ChunkRetriever,
    RetrievedChunk,
    RetrievalUnavailableError,
)
from app.domain.interfaces.vector_store import VectorStore


logger = logging.getLogger(__name__)


class Retriever(ChunkRetriever):
    """Embed a query and retrieve matching chunks through injected ports."""

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
        *,
        min_score: float = 0.25,
        duplicate_similarity: float = 0.90,
    ) -> None:
        if not -1.0 <= min_score <= 1.0:
            raise ValueError("min_score must be between -1 and 1")
        if not 0.0 <= duplicate_similarity <= 1.0:
            raise ValueError("duplicate_similarity must be between 0 and 1")
        self.embedding_provider = embedding_provider
        self.vector_store = vector_store
        self.min_score = min_score
        self.duplicate_similarity = duplicate_similarity

    async def retrieve_relevant_chunks(
        self, query: str, top_k: int = 5
    ) -> list[RetrievedChunk]:
        """Return up to ``top_k`` relevant chunks without provider coupling."""
        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("query cannot be empty")
        if top_k <= 0:
            raise ValueError("top_k must be greater than zero")

        started_at = perf_counter()
        try:
            query_vector = await self.embedding_provider.embed_query(normalized_query)
            results = await self.vector_store.search(
                query_vector,
                limit=max(top_k * 3, top_k),
            )
        except Exception as error:
            logger.warning(
                "RAG retrieval failed: error_type=%s latency_ms=%.2f",
                type(error).__name__,
                (perf_counter() - started_at) * 1000,
            )
            raise RetrievalUnavailableError from error

        threshold_results = [
            result for result in results if result.score >= self.min_score
        ]
        candidates: list[RetrievedChunk] = []
        for result in sorted(
            threshold_results,
            key=lambda item: item.score,
            reverse=True,
        ):
            payload = dict(result.payload)
            text = payload.pop("text", None)
            if not isinstance(text, str) or not text.strip():
                continue
            candidates.append(
                RetrievedChunk(
                    id=result.id,
                    text=text,
                    score=result.score,
                    metadata=payload,
                )
            )

        chunks = self._deduplicate(candidates)[:top_k]
        logger.info(
            (
                "RAG retrieval completed: latency_ms=%.2f retrieved=%s "
                "after_threshold=%s after_deduplication=%s "
                "threshold_removed_all=%s"
            ),
            (perf_counter() - started_at) * 1000,
            len(results),
            len(candidates),
            len(chunks),
            bool(results and not threshold_results),
        )
        return chunks

    def _deduplicate(
        self,
        chunks: list[RetrievedChunk],
    ) -> list[RetrievedChunk]:
        """Keep the highest-scoring representative of repeated chunk text."""
        kept: list[RetrievedChunk] = []
        normalized_kept: list[str] = []
        for chunk in chunks:
            normalized = " ".join(chunk.text.casefold().split())
            if not normalized:
                continue
            if any(
                normalized == existing
                or SequenceMatcher(None, normalized, existing).ratio()
                >= self.duplicate_similarity
                for existing in normalized_kept
            ):
                continue
            kept.append(chunk)
            normalized_kept.append(normalized)
        return kept
