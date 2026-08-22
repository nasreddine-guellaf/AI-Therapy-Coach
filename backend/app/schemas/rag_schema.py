"""Public-safe RAG operational schemas."""

from typing import Literal

from pydantic import BaseModel


class RAGReadinessResponse(BaseModel):
    qdrant_reachable: bool
    collection_exists: bool
    indexed_document_count: int
    total_chunk_count: int
    expected_pdf_count: int
    embedding_model: str
    status: Literal["ready", "not_ready"]

