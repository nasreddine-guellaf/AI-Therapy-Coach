"""Qdrant fixed-knowledge and local embedding adapter tests."""

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Sequence

from app.domain.interfaces.knowledge_base import KnowledgeBaseDocument
from app.domain.interfaces.vector_store import (
    VectorSearchResult,
    VectorStore,
    VectorStoreReadiness,
)
from app.infrastructure.rag.chunker import TextChunker
from app.infrastructure.rag.document_indexer import RAGDocumentIndexer
from app.infrastructure.rag.embeddings import LocalE5EmbeddingProvider
from app.infrastructure.rag.pdf_loader import LoadedPage, PDFLoader
from app.infrastructure.vector_db.qdrant_client import QdrantVectorStore


class FakeQdrantClient:
    def __init__(self) -> None:
        self.created = False
        self.create_count = 0
        self.exists = False
        self.collection_delete_count = 0
        self.indexed_field: str | None = None
        self.upserted = []
        self.deleted_filter = None
        self.query_kwargs = None

    async def collection_exists(self, collection_name: str) -> bool:
        return self.exists

    async def create_collection(self, **kwargs) -> None:
        self.created = True
        self.create_count += 1
        self.exists = True
        assert kwargs["vectors_config"].size == 384

    async def delete_collection(self, collection_name: str) -> None:
        self.collection_delete_count += 1
        self.exists = False
        self.upserted = []

    async def create_payload_index(self, **kwargs) -> None:
        self.indexed_field = kwargs["field_name"]

    async def upsert(self, **kwargs) -> None:
        self.upserted = kwargs["points"]

    async def delete(self, **kwargs) -> None:
        self.deleted_filter = kwargs["points_selector"].filter

    async def query_points(self, **kwargs):
        self.query_kwargs = kwargs
        return SimpleNamespace(
            points=[
                SimpleNamespace(
                    id="10000000-0000-0000-0000-000000000001",
                    score=0.88,
                    payload={"text": "Grounded text"},
                )
            ]
        )

    async def get_collection(self, collection_name: str):
        return SimpleNamespace(points_count=len(self.upserted))

    async def scroll(self, **kwargs):
        return (
            [
                SimpleNamespace(payload=dict(point.payload or {}))
                for point in self.upserted
            ],
            None,
        )


def test_qdrant_collection_supports_global_fixed_knowledge() -> None:
    client = FakeQdrantClient()
    store = QdrantVectorStore(
        collection_name="therapy_knowledge_chunks",
        client=client,
    )
    vector = [0.0] * 384
    asyncio.run(
        store.upsert(
            ["10000000-0000-0000-0000-000000000001"],
            [vector],
            [{"document_id": "doc-1", "text": "Grounded text"}],
        )
    )
    asyncio.run(store.delete_document("doc-1"))
    results = asyncio.run(store.search(vector, limit=3))
    readiness = asyncio.run(store.inspect_readiness())

    assert client.created
    assert client.indexed_field == "document_id"
    assert len(client.upserted) == 1
    assert client.deleted_filter.must[0].match.value == "doc-1"
    assert "query_filter" not in client.query_kwargs
    assert results[0].payload["text"] == "Grounded text"
    assert readiness.indexed_document_count == 1
    assert readiness.total_chunk_count == 1


def test_qdrant_recreate_deletes_and_rebuilds_collection() -> None:
    client = FakeQdrantClient()
    client.exists = True
    store = QdrantVectorStore(
        collection_name="therapy_knowledge_chunks",
        client=client,
    )

    asyncio.run(store.recreate_collection())

    assert client.collection_delete_count == 1
    assert client.create_count == 1
    assert client.exists


class FakeVector(list):
    def tolist(self):
        return list(self)


class FakeSentenceTransformer:
    def encode(self, texts, **kwargs):
        assert texts[0].startswith(("query: ", "passage: "))
        assert kwargs["normalize_embeddings"] is True
        return [FakeVector([0.1] * 384) for _ in texts]


def test_local_embedding_provider_uses_e5_prefixes_and_384_dimensions() -> None:
    provider = LocalE5EmbeddingProvider()
    provider._model = FakeSentenceTransformer()
    document_vector = asyncio.run(provider.embed_documents(["bonjour"]))[0]
    query_vector = asyncio.run(provider.embed_query("stress"))
    assert len(document_vector) == 384
    assert len(query_vector) == 384


class FakePDFLoader(PDFLoader):
    def load(self, content: bytes, filename: str | None = None) -> list[LoadedPage]:
        return [LoadedPage("A grounded coaching passage.", 2)]


class FakeEmbeddingProvider:
    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [[0.1] * 384 for _ in texts]

    async def embed_query(self, query: str) -> list[float]:
        return [0.1] * 384


class FakeVectorStore(VectorStore):
    def __init__(self) -> None:
        self.ids: list[str] = []
        self.payloads: list[dict] = []
        self.deleted_document_id: str | None = None

    async def upsert(self, ids, vectors, payloads) -> None:
        self.ids = list(ids)
        self.payloads = list(payloads)

    async def delete_document(self, document_id: str) -> None:
        self.deleted_document_id = document_id

    async def recreate_collection(self) -> None:
        return None

    async def inspect_readiness(self) -> VectorStoreReadiness:
        return VectorStoreReadiness(True, True, 3, len(self.ids))

    async def search(self, vector, limit=5) -> list[VectorSearchResult]:
        return []


def test_document_indexing_uses_stable_ids_and_global_payload() -> None:
    document = KnowledgeBaseDocument(
        document_id="stable-document-id",
        filename="trusted-guide.pdf",
        created_at=datetime(2026, 7, 28, tzinfo=timezone.utc),
    )
    store = FakeVectorStore()
    indexer = RAGDocumentIndexer(
        FakePDFLoader(),
        TextChunker(),
        FakeEmbeddingProvider(),
        store,
    )

    asyncio.run(indexer.index(document, b"%PDF-test"))
    first_ids = list(store.ids)
    asyncio.run(indexer.index(document, b"%PDF-test"))

    assert store.ids == first_ids
    assert store.deleted_document_id == document.document_id
    assert store.payloads[0]["document_id"] == document.document_id
    assert "user_id" not in store.payloads[0]
