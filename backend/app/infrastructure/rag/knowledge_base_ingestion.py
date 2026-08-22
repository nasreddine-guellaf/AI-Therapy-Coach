"""Filesystem orchestration for the owner-managed fixed knowledge base."""

import hashlib
import json
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
    checksum: str
    indexed_at: str
    chunks_indexed: int


@dataclass(frozen=True, slots=True)
class KnowledgeBaseIngestionResult:
    documents: tuple[IndexedKnowledgeDocument, ...]
    manifest_path: Path

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
        *,
        embedding_model: str,
        collection_name: str,
    ) -> None:
        self._directory = knowledge_base_dir
        self._indexer = indexer
        self._embedding_model = embedding_model
        self._collection_name = collection_name
        self._manifest_path = self._directory / "manifest.json"

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

        contents = {path: path.read_bytes() for path in pdf_files}
        checksums = {
            path: hashlib.sha256(content).hexdigest()
            for path, content in contents.items()
        }
        self._reject_duplicate_pdfs(checksums)
        previous_documents = self._load_previous_manifest()
        current_names = {path.name for path in pdf_files}
        missing_names = sorted(set(previous_documents) - current_names)
        if missing_names:
            logger.warning(
                "Knowledge base PDFs missing since previous ingestion: count=%s",
                len(missing_names),
            )
        for path, checksum in checksums.items():
            previous = previous_documents.get(path.name)
            if previous and previous.get("checksum") != checksum:
                logger.warning(
                    "Knowledge base PDF changed: filename=%s checksum_changed=true",
                    path.name,
                )

        indexed: list[IndexedKnowledgeDocument] = []
        indexed_at = datetime.now(timezone.utc).isoformat()
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
                contents[path],
            )
            indexed.append(
                IndexedKnowledgeDocument(
                    filename=path.name,
                    checksum=checksums[path],
                    indexed_at=indexed_at,
                    chunks_indexed=chunks_indexed,
                )
            )

        self._write_manifest(indexed, indexed_at)
        return KnowledgeBaseIngestionResult(
            tuple(indexed),
            self._manifest_path,
        )

    def _load_previous_manifest(self) -> dict[str, dict]:
        if not self._manifest_path.exists():
            return {}
        try:
            manifest = json.loads(self._manifest_path.read_text(encoding="utf-8"))
            documents = manifest.get("documents", [])
            if not isinstance(documents, list):
                raise ValueError
            return {
                item["filename"]: item
                for item in documents
                if isinstance(item, dict)
                and isinstance(item.get("filename"), str)
            }
        except (OSError, ValueError, json.JSONDecodeError) as error:
            raise KnowledgeBaseConfigurationError(
                f"Knowledge base manifest is invalid: {self._manifest_path}"
            ) from error

    @staticmethod
    def _reject_duplicate_pdfs(checksums: dict[Path, str]) -> None:
        by_checksum: dict[str, list[str]] = {}
        for path, checksum in checksums.items():
            by_checksum.setdefault(checksum, []).append(path.name)
        duplicates = [
            filenames for filenames in by_checksum.values() if len(filenames) > 1
        ]
        if duplicates:
            duplicate_names = ", ".join(sorted(duplicates[0]))
            raise KnowledgeBaseConfigurationError(
                f"Duplicate PDF content detected: {duplicate_names}"
            )

    def _write_manifest(
        self,
        documents: list[IndexedKnowledgeDocument],
        indexed_at: str,
    ) -> None:
        payload = {
            "generated_at": indexed_at,
            "embedding_model": self._embedding_model,
            "collection_name": self._collection_name,
            "documents": [
                {
                    "filename": document.filename,
                    "checksum": document.checksum,
                    "indexed_at": document.indexed_at,
                    "chunk_count": document.chunks_indexed,
                    "embedding_model": self._embedding_model,
                    "collection_name": self._collection_name,
                }
                for document in documents
            ],
        }
        temporary_path = self._manifest_path.with_suffix(".json.tmp")
        temporary_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        temporary_path.replace(self._manifest_path)
