"""Tests for the owner-managed fixed knowledge-base ingestion flow."""

import asyncio
import json
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
from app.scripts.ingest_knowledge_base import _preflight_recreate
from app.main import app


class FakeKnowledgeBaseIndexer(KnowledgeBaseIndexer):
    def __init__(self) -> None:
        self.documents: list[KnowledgeBaseDocument] = []

    async def index(self, document: KnowledgeBaseDocument, content: bytes) -> int:
        assert content.startswith(b"%PDF-")
        self.documents.append(document)
        return 2


def build_service(
    directory: Path,
    indexer: KnowledgeBaseIndexer | None = None,
) -> KnowledgeBaseIngestionService:
    return KnowledgeBaseIngestionService(
        directory,
        indexer or FakeKnowledgeBaseIndexer(),
        embedding_model="intfloat/multilingual-e5-small",
        collection_name="therapy_knowledge_chunks",
    )


def test_missing_knowledge_base_directory_fails(tmp_path: Path) -> None:
    service = build_service(tmp_path / "missing")
    with pytest.raises(
        KnowledgeBaseConfigurationError,
        match="directory does not exist",
    ):
        asyncio.run(service.ingest())


def test_knowledge_base_without_pdfs_fails(tmp_path: Path) -> None:
    service = build_service(tmp_path)
    with pytest.raises(KnowledgeBaseConfigurationError, match="No PDF files"):
        asyncio.run(service.ingest())


def test_three_fixed_pdfs_are_indexed_with_stable_ids(tmp_path: Path) -> None:
    for index, filename in enumerate(
        ("guide-a.pdf", "guide-b.PDF", "guide-c.pdf"),
        start=1,
    ):
        (tmp_path / filename).write_bytes(f"%PDF-test-{index}".encode())

    first_indexer = FakeKnowledgeBaseIndexer()
    first = asyncio.run(
        build_service(tmp_path, first_indexer).ingest()
    )
    second_indexer = FakeKnowledgeBaseIndexer()
    second = asyncio.run(
        build_service(tmp_path, second_indexer).ingest()
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
            build_service(tmp_path).ingest()
        )
    assert "expected=3 actual=1" in caplog.text


def test_manifest_contains_only_operational_metadata(tmp_path: Path) -> None:
    for index in range(3):
        (tmp_path / f"guide-{index}.pdf").write_bytes(
            f"%PDF-content-{index}".encode()
        )
    result = asyncio.run(build_service(tmp_path).ingest())
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))

    assert manifest["embedding_model"] == "intfloat/multilingual-e5-small"
    assert manifest["collection_name"] == "therapy_knowledge_chunks"
    assert len(manifest["documents"]) == 3
    assert {
        "filename",
        "checksum",
        "indexed_at",
        "chunk_count",
        "embedding_model",
        "collection_name",
    } <= manifest["documents"][0].keys()
    assert "text" not in result.manifest_path.read_text(encoding="utf-8")


def test_changed_and_missing_pdfs_are_detected(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    for index in range(3):
        (tmp_path / f"guide-{index}.pdf").write_bytes(
            f"%PDF-original-{index}".encode()
        )
    asyncio.run(build_service(tmp_path).ingest())
    (tmp_path / "guide-0.pdf").write_bytes(b"%PDF-changed")
    (tmp_path / "guide-1.pdf").unlink()
    (tmp_path / "replacement.pdf").write_bytes(b"%PDF-replacement")

    with caplog.at_level(logging.WARNING):
        asyncio.run(build_service(tmp_path).ingest())

    assert "checksum_changed=true" in caplog.text
    assert "PDFs missing since previous ingestion: count=1" in caplog.text


def test_duplicate_pdf_content_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "guide-a.pdf").write_bytes(b"%PDF-same")
    (tmp_path / "guide-b.pdf").write_bytes(b"%PDF-same")
    (tmp_path / "guide-c.pdf").write_bytes(b"%PDF-distinct")
    with pytest.raises(KnowledgeBaseConfigurationError, match="Duplicate PDF"):
        asyncio.run(build_service(tmp_path).ingest())


def test_recreate_preflight_requires_exactly_three_pdfs(tmp_path: Path) -> None:
    (tmp_path / "guide-a.pdf").write_bytes(b"%PDF-a")
    (tmp_path / "guide-b.pdf").write_bytes(b"%PDF-b")
    with pytest.raises(KnowledgeBaseConfigurationError, match="exactly 3"):
        _preflight_recreate(tmp_path)


def test_recreate_preflight_rejects_duplicates_before_qdrant(tmp_path: Path) -> None:
    (tmp_path / "guide-a.pdf").write_bytes(b"%PDF-same")
    (tmp_path / "guide-b.pdf").write_bytes(b"%PDF-same")
    (tmp_path / "guide-c.pdf").write_bytes(b"%PDF-distinct")
    with pytest.raises(KnowledgeBaseConfigurationError, match="duplicate"):
        _preflight_recreate(tmp_path)


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
