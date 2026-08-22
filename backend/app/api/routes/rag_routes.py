"""Authenticated operational HTTP adapter for fixed-knowledge RAG."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.auth_dependencies import get_current_user
from app.api.dependencies import get_rag_readiness_service
from app.domain.entities.user import User
from app.domain.services.rag_readiness_service import RAGReadinessService
from app.schemas.rag_schema import RAGReadinessResponse


router = APIRouter(prefix="/rag", tags=["rag"])


@router.get("/readiness", response_model=RAGReadinessResponse)
async def get_rag_readiness(
    service: Annotated[RAGReadinessService, Depends(get_rag_readiness_service)],
    _current_user: Annotated[User, Depends(get_current_user)],
) -> RAGReadinessResponse:
    """Return aggregate RAG state without document or conversation content."""
    result = await service.check()
    return RAGReadinessResponse(
        qdrant_reachable=result.qdrant_reachable,
        collection_exists=result.collection_exists,
        indexed_document_count=result.indexed_document_count,
        total_chunk_count=result.total_chunk_count,
        expected_pdf_count=result.expected_pdf_count,
        embedding_model=result.embedding_model,
        status=result.status,
    )

