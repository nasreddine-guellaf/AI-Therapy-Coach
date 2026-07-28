"""Tests for the owner-managed fixed knowledge-base ingestion flow."""

import asyncio
import logging
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from app.domain.interfaces.knowledge_base import (
    KnowledgeBaseConfigurationError,
    KnowledgeBaseDocument,
    KnowledgeBaseIndexer,
    NoExtractableTextError,
)
from app.infrastructure.rag.knowledge_base_ingestion import (
    KnowledgeBaseIngestionService,
)
from app.infrastructure.rag.pdf_loader import PyPDFTextLoader
from app.main import app


class FakeKnowledgeBaseIndexer(KnowledgeBaseIndexer):
    def __init__(self) -> None:
        self.documents: list[KnowledgeBaseDocument] = []

    async def index(self, document: KnowledgeBaseDocument, content: bytes) -> int:
        assert content.startswith(b"%PDF-")
        self.documents.append(document)
        return 2


def test_missing_knowledge_base_directory_fails(tmp_path: Path) -> None:
    service = KnowledgeBaseIngestionService(
        tmp_path / "missing",
        FakeKnowledgeBaseIndexer(),
    )
    with pytest.raises(
        KnowledgeBaseConfigurationError,
        match="directory does not exist",
    ):
        asyncio.run(service.ingest())


def test_knowledge_base_without_pdfs_fails(tmp_path: Path) -> None:
    service = KnowledgeBaseIngestionService(tmp_path, FakeKnowledgeBaseIndexer())
    with pytest.raises(KnowledgeBaseConfigurationError, match="No PDF files"):
        asyncio.run(service.ingest())


def test_three_fixed_pdfs_are_indexed_with_stable_ids(tmp_path: Path) -> None:
    for filename in ("guide-a.pdf", "guide-b.PDF", "guide-c.pdf"):
        (tmp_path / filename).write_bytes(b"%PDF-test")

    first_indexer = FakeKnowledgeBaseIndexer()
    first = asyncio.run(
        KnowledgeBaseIngestionService(tmp_path, first_indexer).ingest()
    )
    second_indexer = FakeKnowledgeBaseIndexer()
    second = asyncio.run(
        KnowledgeBaseIngestionService(tmp_path, second_indexer).ingest()
    )

    assert len(first.documents) == 3
    assert first.chunks_indexed == 6
    assert second.chunks_indexed == 6
    assert [item.document_id for item in first_indexer.documents] == [
        item.document_id for item in second_indexer.documents
    ]


def test_unexpected_pdf_count_emits_warning(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    (tmp_path / "only-one.pdf").write_bytes(b"%PDF-test")
    with caplog.at_level(logging.WARNING):
        asyncio.run(
            KnowledgeBaseIngestionService(
                tmp_path,
                FakeKnowledgeBaseIndexer(),
            ).ingest()
        )
    assert "expected=3 actual=1" in caplog.text


def test_scanned_or_empty_text_pdf_reports_ocr_limitation() -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    payload = BytesIO()
    writer.write(payload)
    with pytest.raises(
        NoExtractableTextError,
        match="No extractable text found. OCR is not supported yet.",
    ):
        PyPDFTextLoader().load(payload.getvalue(), "scan.pdf")


def test_public_document_upload_route_is_not_exposed() -> None:
    response = TestClient(app).post(
        "/api/documents/upload",
        files={"file": ("notes.pdf", b"%PDF-test", "application/pdf")},
    )
    assert response.status_code == 404
