import asyncio
import logging
from typing import Sequence

import pytest

from app.domain.interfaces.vector_store import (
    VectorSearchResult,
    VectorStore,
    VectorStoreReadiness,
)
from app.infrastructure.rag.embeddings import EmbeddingProvider
from app.infrastructure.rag.retriever import Retriever


class StubEmbeddingProvider(EmbeddingProvider):
    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [[0.1, 0.2] for _ in texts]

    async def embed_query(self, query: str) -> list[float]:
        return [0.1, 0.2]


class StubVectorStore(VectorStore):
    def __init__(
        self,
        results: list[VectorSearchResult] | None = None,
    ) -> None:
        self.last_limit: int | None = None
        self.results = results

    async def upsert(
        self,
        ids: Sequence[str],
        vectors: Sequence[Sequence[float]],
        payloads: Sequence[dict],
    ) -> None:
        return None

    async def delete_document(self, document_id: str) -> None:
        return None

    async def recreate_collection(self) -> None:
        return None

    async def inspect_readiness(self) -> VectorStoreReadiness:
        return VectorStoreReadiness(True, True, 3, 10)

    async def search(
        self, vector: Sequence[float], limit: int = 5
    ) -> list[VectorSearchResult]:
        self.last_limit = limit
        return self.results if self.results is not None else [
            VectorSearchResult(
                id="chunk-1",
                score=0.94,
                payload={
                    "text": "Grounded coaching context",
                    "source_id": "source-1",
                    "filename": "guide.pdf",
                    "page_number": 2,
                    "chunk_index": 4,
                },
            )
        ]


def test_retrieve_relevant_chunks_uses_injected_ports() -> None:
    store = StubVectorStore()
    retriever = Retriever(StubEmbeddingProvider(), store)

    chunks = asyncio.run(retriever.retrieve_relevant_chunks("stress", top_k=3))

    assert store.last_limit == 9
    assert chunks[0].text == "Grounded coaching context"
    assert chunks[0].source_id == "source-1"
    assert chunks[0].filename == "guide.pdf"


def test_retriever_rejects_empty_query() -> None:
    retriever = Retriever(StubEmbeddingProvider(), StubVectorStore())

    try:
        asyncio.run(
            retriever.retrieve_relevant_chunks(
                "   ",
                top_k=3,
            )
        )
    except ValueError as error:
        assert "query cannot be empty" in str(error)
    else:
        raise AssertionError("An empty query should be rejected")


def test_retriever_filters_chunks_below_minimum_score_without_logging_query(
    caplog: pytest.LogCaptureFixture,
) -> None:
    store = StubVectorStore(
        [
            VectorSearchResult(
                id="weak",
                score=0.24,
                payload={"text": "Weak unrelated context"},
            )
        ]
    )
    retriever = Retriever(
        StubEmbeddingProvider(),
        store,
        min_score=0.25,
    )

    sensitive_query = "private user message must not be logged"
    with caplog.at_level(logging.INFO):
        chunks = asyncio.run(
            retriever.retrieve_relevant_chunks(sensitive_query, top_k=4)
        )

    assert chunks == []
    assert "retrieved=1" in caplog.text
    assert "threshold_removed_all=True" in caplog.text
    assert sensitive_query not in caplog.text


def test_retriever_deduplicates_and_keeps_highest_score() -> None:
    store = StubVectorStore(
        [
            VectorSearchResult(
                id="highest",
                score=0.92,
                payload={
                    "text": "Take one small achievable step and reflect on it.",
                    "source_id": "source-high",
                },
            ),
            VectorSearchResult(
                id="duplicate",
                score=0.71,
                payload={
                    "text": "  take ONE small achievable step and reflect on it. ",
                    "source_id": "source-low",
                },
            ),
            VectorSearchResult(
                id="distinct",
                score=0.66,
                payload={
                    "text": "Ask an open question and listen without judgment.",
                    "source_id": "source-distinct",
                },
            ),
        ]
    )
    retriever = Retriever(StubEmbeddingProvider(), store, min_score=0.25)

    chunks = asyncio.run(retriever.retrieve_relevant_chunks("question", top_k=4))

    assert [chunk.source_id for chunk in chunks] == [
        "source-high",
        "source-distinct",
    ]


def test_retriever_returns_empty_when_vector_store_has_no_results() -> None:
    retriever = Retriever(
        StubEmbeddingProvider(),
        StubVectorStore([]),
        min_score=0.25,
    )
    assert asyncio.run(
        retriever.retrieve_relevant_chunks("unknown topic", top_k=4)
    ) == []
