import pytest

from app.infrastructure.rag.chunker import TextChunker
from app.infrastructure.rag.pdf_loader import LoadedPage


def test_chunker_preserves_page_metadata_and_size_limit() -> None:
    page = LoadedPage(
        text="alpha beta gamma delta epsilon zeta eta theta iota kappa lambda",
        page_number=3,
        metadata={"document_id": "doc-1"},
    )

    chunks = TextChunker(chunk_size=24, chunk_overlap=5).chunk([page])

    assert len(chunks) > 1
    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))
    assert all(len(chunk.text) <= 24 for chunk in chunks)
    assert all(chunk.page_number == 3 for chunk in chunks)
    assert all(chunk.metadata["document_id"] == "doc-1" for chunk in chunks)


def test_chunker_skips_empty_pages() -> None:
    chunks = TextChunker().chunk([LoadedPage(text="   ", page_number=1)])
    assert chunks == []


def test_chunker_rejects_overlap_equal_to_chunk_size() -> None:
    with pytest.raises(ValueError, match="smaller"):
        TextChunker(chunk_size=100, chunk_overlap=100)
