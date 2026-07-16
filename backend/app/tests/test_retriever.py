import asyncio
from typing import Sequence

from app.domain.interfaces.vector_store import VectorSearchResult, VectorStore
from app.infrastructure.rag.embeddings import EmbeddingProvider
from app.infrastructure.rag.retriever import Retriever


class StubEmbeddingProvider(EmbeddingProvider):
    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [[0.1, 0.2] for _ in texts]

    async def embed_query(self, query: str) -> list[float]:
        return [0.1, 0.2]


class StubVectorStore(VectorStore):
    def __init__(self) -> None:
        self.last_limit: int | None = None

    async def upsert(
        self,
        ids: Sequence[str],
        vectors: Sequence[Sequence[float]],
        payloads: Sequence[dict],
    ) -> None:
        return None

    async def search(
        self, vector: Sequence[float], limit: int = 5
    ) -> list[VectorSearchResult]:
        self.last_limit = limit
        return [
            VectorSearchResult(
                id="chunk-1",
                score=0.94,
                payload={"text": "Grounded coaching context", "page_number": 2},
            )
        ]


def test_retrieve_relevant_chunks_uses_injected_ports() -> None:
    store = StubVectorStore()
    retriever = Retriever(StubEmbeddingProvider(), store)

    chunks = asyncio.run(retriever.retrieve_relevant_chunks("stress", top_k=3))

    assert store.last_limit == 3
    assert chunks[0].text == "Grounded coaching context"
    assert chunks[0].metadata == {"page_number": 2}


def test_retriever_rejects_empty_query() -> None:
    retriever = Retriever(StubEmbeddingProvider(), StubVectorStore())

    try:
        asyncio.run(retriever.retrieve_relevant_chunks("   ", top_k=3))
    except ValueError as error:
        assert "query cannot be empty" in str(error)
    else:
        raise AssertionError("An empty query should be rejected")
