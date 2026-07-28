"""PDF loading contract and page representation for RAG ingestion."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.domain.interfaces.knowledge_base import (
    DocumentValidationError,
    NoExtractableTextError,
)


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


class PyPDFTextLoader(PDFLoader):
    """Extract page text from non-encrypted, text-based PDF files."""

    def load(self, content: bytes, filename: str | None = None) -> list[LoadedPage]:
        if not content or not content.startswith(b"%PDF-"):
            raise ValueError("Content does not have a valid PDF signature")
        try:
            reader = PdfReader(BytesIO(content), strict=False)
            if reader.is_encrypted:
                raise DocumentValidationError("Encrypted PDF files are not supported")
            pages = [
                LoadedPage(
                    text=(page.extract_text() or "").strip(),
                    page_number=index,
                    metadata={"filename": filename or "document.pdf"},
                )
                for index, page in enumerate(reader.pages, start=1)
            ]
        except (PdfReadError, EOFError) as error:
            raise DocumentValidationError("The PDF could not be parsed") from error

        if not any(page.text for page in pages):
            raise NoExtractableTextError(
                "No extractable text found. OCR is not supported yet."
            )
        return pages
