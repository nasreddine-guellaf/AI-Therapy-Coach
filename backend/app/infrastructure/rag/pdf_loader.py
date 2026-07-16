"""PDF loading contract and page representation for RAG ingestion."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class LoadedPage:
    """Text extracted from one PDF page with traceable source metadata."""

    text: str
    page_number: int
    metadata: dict[str, Any] = field(default_factory=dict)


class PDFLoader(ABC):
    """Port for converting PDF bytes into page-level text.

    Concrete parsers must live behind this contract so ingestion is not coupled
    to PyPDF, Unstructured, or a cloud document service.
    """

    @abstractmethod
    def load(self, content: bytes, filename: str | None = None) -> list[LoadedPage]:
        """Extract ordered pages from a validated PDF payload."""
        raise NotImplementedError


class PlaceholderPDFLoader(PDFLoader):
    """Explicit no-network/no-parser adapter used until a parser is selected."""

    def load(self, content: bytes, filename: str | None = None) -> list[LoadedPage]:
        if not content:
            raise ValueError("PDF content cannot be empty")
        if not content.startswith(b"%PDF-"):
            raise ValueError("Content does not have a PDF signature")

        # TODO: integrate a sandboxed PDF parser, page limits, malware scanning,
        # encrypted-file handling, and extraction quality metrics.
        raise NotImplementedError("A production PDF parser has not been configured")
