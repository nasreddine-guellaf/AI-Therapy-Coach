"""Index the project owner's fixed PDF knowledge base into Qdrant."""

import asyncio
import logging
from pathlib import Path

from app.core.config import settings
from app.domain.interfaces.knowledge_base import (
    DocumentValidationError,
    KnowledgeBaseError,
)
from app.infrastructure.rag.chunker import TextChunker
from app.infrastructure.rag.document_indexer import RAGDocumentIndexer
from app.infrastructure.rag.embeddings import LocalE5EmbeddingProvider
from app.infrastructure.rag.knowledge_base_ingestion import (
    KnowledgeBaseIngestionService,
)
from app.infrastructure.rag.pdf_loader import PyPDFTextLoader
from app.infrastructure.vector_db.qdrant_client import QdrantVectorStore


def resolve_knowledge_base_dir(configured: Path) -> Path:
    """Resolve the documented project-root path from host or backend cwd."""
    if configured.is_absolute():
        return configured

    backend_root = Path(__file__).resolve().parents[2]
    if configured.parts[:1] == ("backend",):
        if backend_root.name == "backend":
            return backend_root.parent / configured
        return backend_root.joinpath(*configured.parts[1:])

    project_root = backend_root.parent
    project_candidate = project_root / configured
    if project_candidate.exists():
        return project_candidate
    return backend_root / configured


async def ingest() -> int:
    service = KnowledgeBaseIngestionService(
        resolve_knowledge_base_dir(settings.knowledge_base_dir),
        RAGDocumentIndexer(
            pdf_loader=PyPDFTextLoader(),
            chunker=TextChunker(),
            embedding_provider=LocalE5EmbeddingProvider(settings.embedding_model),
            vector_store=QdrantVectorStore(),
        ),
    )
    result = await service.ingest()
    for document in result.documents:
        print(f"Indexed {document.filename}: {document.chunks_indexed} chunks")
    print(
        f"Knowledge base indexed: {len(result.documents)} PDFs, "
        f"{result.chunks_indexed} chunks"
    )
    return 0


def main() -> int:
    logging.basicConfig(level=logging.INFO)
    try:
        return asyncio.run(ingest())
    except (KnowledgeBaseError, DocumentValidationError) as error:
        print(f"Knowledge base ingestion failed: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
