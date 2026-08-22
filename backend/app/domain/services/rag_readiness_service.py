"""Provider-neutral readiness use case for the fixed RAG knowledge base."""

from dataclasses import dataclass

from app.domain.interfaces.vector_store import VectorStore


@dataclass(frozen=True, slots=True)
class RAGReadiness:
    qdrant_reachable: bool
    collection_exists: bool
    indexed_document_count: int
    total_chunk_count: int
    expected_pdf_count: int
    embedding_model: str
    status: str


class RAGReadinessService:
    """Convert vector-store aggregates into a stable readiness contract."""

    def __init__(
        self,
        vector_store: VectorStore,
        *,
        expected_pdf_count: int,
        embedding_model: str,
    ) -> None:
        self._vector_store = vector_store
        self._expected_pdf_count = expected_pdf_count
        self._embedding_model = embedding_model

    async def check(self) -> RAGReadiness:
        state = await self._vector_store.inspect_readiness()
        ready = (
            state.qdrant_reachable
            and state.collection_exists
            and state.indexed_document_count == self._expected_pdf_count
            and state.total_chunk_count > 0
        )
        return RAGReadiness(
            qdrant_reachable=state.qdrant_reachable,
            collection_exists=state.collection_exists,
            indexed_document_count=state.indexed_document_count,
            total_chunk_count=state.total_chunk_count,
            expected_pdf_count=self._expected_pdf_count,
            embedding_model=self._embedding_model,
            status="ready" if ready else "not_ready",
        )
