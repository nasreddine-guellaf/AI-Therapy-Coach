"""Infrastructure pipeline for PDF extraction through Qdrant indexing."""

import asyncio
from datetime import timezone
from uuid import NAMESPACE_URL, uuid5

from app.domain.interfaces.knowledge_base import (
    DocumentIndexingError,
    DocumentValidationError,
    KnowledgeBaseDocument,
    KnowledgeBaseIndexer,
    NoExtractableTextError,
)
from app.domain.interfaces.embedding_provider import EmbeddingProvider
from app.domain.interfaces.vector_store import VectorStore
from app.infrastructure.rag.chunker import TextChunker
from app.infrastructure.rag.pdf_loader import PDFLoader


class RAGDocumentIndexer(KnowledgeBaseIndexer):
    def __init__(
        self,
        pdf_loader: PDFLoader,
        chunker: TextChunker,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
    ) -> None:
        self._pdf_loader = pdf_loader
        self._chunker = chunker
        self._embeddings = embedding_provider
        self._vector_store = vector_store

    async def index(self, document: KnowledgeBaseDocument, content: bytes) -> int:
        try:
            pages = await asyncio.to_thread(
                self._pdf_loader.load, content, document.filename
            )
            chunks = await asyncio.to_thread(self._chunker.chunk, pages)
            if not chunks:
                raise NoExtractableTextError(
                    "No extractable text found. OCR is not supported yet."
                )
            vectors = await self._embeddings.embed_documents(
                [chunk.text for chunk in chunks]
            )
            created_at = document.created_at.astimezone(timezone.utc).isoformat()
            source_ids = [
                str(
                    uuid5(
                        NAMESPACE_URL,
                        (
                            "therapy-knowledge:"
                            f"{document.filename.casefold()}:"
                            f"{chunk.page_number}:{chunk.chunk_index}"
                        ),
                    )
                )
                for chunk in chunks
            ]
            payloads = [
                {
                    "document_id": document.document_id,
                    "filename": document.filename,
                    "source_id": source_id,
                    "page_number": chunk.page_number,
                    "chunk_index": chunk.chunk_index,
                    "text": chunk.text,
                    "created_at": created_at,
                }
                for source_id, chunk in zip(source_ids, chunks, strict=True)
            ]
            await self._vector_store.delete_document(document.document_id)
            await self._vector_store.upsert(source_ids, vectors, payloads)
            return len(chunks)
        except DocumentValidationError:
            raise
        except Exception as error:
            raise DocumentIndexingError from error
