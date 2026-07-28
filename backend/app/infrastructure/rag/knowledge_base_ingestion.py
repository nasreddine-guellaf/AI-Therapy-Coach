"""Filesystem orchestration for the owner-managed fixed knowledge base."""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from app.domain.interfaces.knowledge_base import (
    KnowledgeBaseConfigurationError,
    KnowledgeBaseDocument,
    KnowledgeBaseIndexer,
)


logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class IndexedKnowledgeDocument:
    filename: str
    chunks_indexed: int


@dataclass(frozen=True, slots=True)
class KnowledgeBaseIngestionResult:
    documents: tuple[IndexedKnowledgeDocument, ...]

    @property
    def chunks_indexed(self) -> int:
        return sum(document.chunks_indexed for document in self.documents)


class KnowledgeBaseIngestionService:
    """Discover trusted PDFs and delegate extraction/indexing through a port."""

    EXPECTED_PDF_COUNT = 3

    def __init__(
        self,
        knowledge_base_dir: Path,
        indexer: KnowledgeBaseIndexer,
    ) -> None:
        self._directory = knowledge_base_dir
        self._indexer = indexer

    async def ingest(self) -> KnowledgeBaseIngestionResult:
        if not self._directory.is_dir():
            raise KnowledgeBaseConfigurationError(
                f"Knowledge base directory does not exist: {self._directory}"
            )

        pdf_files = sorted(
            (
                path
                for path in self._directory.iterdir()
                if path.is_file() and path.suffix.casefold() == ".pdf"
            ),
            key=lambda path: path.name.casefold(),
        )
        if not pdf_files:
            raise KnowledgeBaseConfigurationError(
                f"No PDF files found in knowledge base directory: {self._directory}"
            )
        if len(pdf_files) != self.EXPECTED_PDF_COUNT:
            logger.warning(
                "Knowledge base PDF count differs from expected: expected=%s actual=%s",
                self.EXPECTED_PDF_COUNT,
                len(pdf_files),
            )

        indexed: list[IndexedKnowledgeDocument] = []
        for path in pdf_files:
            stat = path.stat()
            document = KnowledgeBaseDocument(
                document_id=str(
                    uuid5(
                        NAMESPACE_URL,
                        f"therapy-knowledge-document:{path.name.casefold()}",
                    )
                ),
                filename=path.name,
                created_at=datetime.fromtimestamp(
                    stat.st_mtime,
                    tz=timezone.utc,
                ),
            )
            chunks_indexed = await self._indexer.index(
                document,
                path.read_bytes(),
            )
            indexed.append(
                IndexedKnowledgeDocument(
                    filename=path.name,
                    chunks_indexed=chunks_indexed,
                )
            )

        return KnowledgeBaseIngestionResult(tuple(indexed))

