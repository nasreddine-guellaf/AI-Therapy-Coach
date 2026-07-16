"""Deterministic, overlap-aware text chunking for PDF pages."""

from dataclasses import dataclass, field
from typing import Any

from app.infrastructure.rag.pdf_loader import LoadedPage


@dataclass(frozen=True, slots=True)
class TextChunk:
    """A retrievable text unit retaining its page and character provenance."""

    text: str
    page_number: int
    chunk_index: int
    start_char: int
    end_char: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        """Return the minimal payload intended for a vector store."""
        return {
            "text": self.text,
            "page_number": self.page_number,
            "chunk_index": self.chunk_index,
            "start_char": self.start_char,
            "end_char": self.end_char,
            **self.metadata,
        }


class TextChunker:
    """Split each page into bounded character chunks with configurable overlap."""

    def __init__(self, chunk_size: int = 1_000, chunk_overlap: int = 150) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than zero")
        if chunk_overlap < 0:
            raise ValueError("chunk_overlap cannot be negative")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk(self, pages: list[LoadedPage]) -> list[TextChunk]:
        """Chunk pages independently so citations never cross page boundaries."""
        chunks: list[TextChunk] = []
        chunk_index = 0

        for page in pages:
            text = page.text.strip()
            if not text:
                continue

            start = 0
            while start < len(text):
                end = self._choose_end(text, start)
                chunk_text = text[start:end].strip()
                if chunk_text:
                    chunks.append(
                        TextChunk(
                            text=chunk_text,
                            page_number=page.page_number,
                            chunk_index=chunk_index,
                            start_char=start,
                            end_char=end,
                            metadata=dict(page.metadata),
                        )
                    )
                    chunk_index += 1

                if end >= len(text):
                    break
                # A very large overlap combined with an early word boundary
                # must still advance, otherwise chunking could loop forever.
                start = max(end - self.chunk_overlap, start + 1)

        # TODO: consider tokenizer-aware sizing and semantic boundaries once the
        # embedding model and its token limits are selected.
        return chunks

    def _choose_end(self, text: str, start: int) -> int:
        hard_end = min(start + self.chunk_size, len(text))
        if hard_end == len(text):
            return hard_end

        minimum_boundary = start + (self.chunk_size // 2)
        newline = text.rfind("\n", minimum_boundary, hard_end)
        whitespace = text.rfind(" ", minimum_boundary, hard_end)
        boundary = max(newline, whitespace)
        return boundary if boundary > start else hard_end
