"""Authenticated, content-free RAG readiness contract tests."""

import asyncio
from datetime import datetime, timezone
from typing import Sequence
from uuid import UUID

from fastapi.testclient import TestClient

from app.api.auth_dependencies import get_current_user
from app.api.dependencies import get_rag_readiness_service
from app.domain.entities.user import User
from app.domain.interfaces.vector_store import (
    VectorSearchResult,
    VectorStore,
    VectorStoreReadiness,
)
from app.domain.services.rag_readiness_service import RAGReadinessService
from app.main import app


USER_ID = UUID("00000000-0000-0000-0000-000000000001")
NOW = datetime.now(timezone.utc)


class ReadinessVectorStore(VectorStore):
    def __init__(self, state: VectorStoreReadiness) -> None:
        self.state = state

    async def upsert(self, ids, vectors, payloads) -> None:
        return None

    async def delete_document(self, document_id: str) -> None:
        return None

    async def recreate_collection(self) -> None:
        return None

    async def inspect_readiness(self) -> VectorStoreReadiness:
        return self.state

    async def search(
        self,
        vector: Sequence[float],
        limit: int = 5,
    ) -> list[VectorSearchResult]:
        return []


def test_readiness_service_requires_exactly_three_indexed_documents() -> None:
    ready = RAGReadinessService(
        ReadinessVectorStore(VectorStoreReadiness(True, True, 3, 42)),
        expected_pdf_count=3,
        embedding_model="test-model",
    )
    not_ready = RAGReadinessService(
        ReadinessVectorStore(VectorStoreReadiness(True, True, 2, 20)),
        expected_pdf_count=3,
        embedding_model="test-model",
    )

    assert asyncio.run(ready.check()).status == "ready"
    assert asyncio.run(not_ready.check()).status == "not_ready"


def test_rag_readiness_endpoint_requires_authentication() -> None:
    response = TestClient(app).get("/api/rag/readiness")
    assert response.status_code == 401


def test_rag_readiness_endpoint_returns_only_safe_aggregates() -> None:
    service = RAGReadinessService(
        ReadinessVectorStore(VectorStoreReadiness(True, True, 3, 42)),
        expected_pdf_count=3,
        embedding_model="intfloat/multilingual-e5-small",
    )
    user = User(
        id=USER_ID,
        email="person@example.com",
        hashed_password="hash",
        full_name=None,
        is_active=True,
        created_at=NOW,
        updated_at=NOW,
    )
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_rag_readiness_service] = lambda: service
    try:
        response = TestClient(app).get(
            "/api/rag/readiness",
            headers={"Authorization": "Bearer test"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "qdrant_reachable": True,
        "collection_exists": True,
        "indexed_document_count": 3,
        "total_chunk_count": 42,
        "expected_pdf_count": 3,
        "embedding_model": "intfloat/multilingual-e5-small",
        "status": "ready",
    }
    assert "text" not in response.text

