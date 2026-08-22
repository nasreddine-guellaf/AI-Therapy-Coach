"""Index the project owner's fixed PDF knowledge base into Qdrant."""

import argparse
import asyncio
import hashlib
import logging
from pathlib import Path

from app.core.config import settings
from app.domain.interfaces.knowledge_base import (
    DocumentValidationError,
    KnowledgeBaseConfigurationError,
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


async def ingest(*, recreate: bool = False) -> int:
    knowledge_base_dir = resolve_knowledge_base_dir(settings.knowledge_base_dir)
    if recreate:
        _preflight_recreate(knowledge_base_dir)

    vector_store = QdrantVectorStore()
    if recreate:
        await vector_store.recreate_collection()

    service = KnowledgeBaseIngestionService(
        knowledge_base_dir,
        RAGDocumentIndexer(
            pdf_loader=PyPDFTextLoader(),
            chunker=TextChunker(),
            embedding_provider=LocalE5EmbeddingProvider(settings.embedding_model),
            vector_store=vector_store,
        ),
        embedding_model=settings.embedding_model,
        collection_name=settings.rag_collection_name,
    )
    result = await service.ingest()
    for document in result.documents:
        print(f"Indexed {document.filename}: {document.chunks_indexed} chunks")
    print(
        f"Knowledge base indexed: {len(result.documents)} PDFs, "
        f"{result.chunks_indexed} chunks"
    )
    print(f"Manifest written: {result.manifest_path}")
    return 0


def _preflight_recreate(knowledge_base_dir: Path) -> None:
    """Fully validate the three source files before destructive recreation."""
    pdf_files = (
        sorted(
            (
                path
                for path in knowledge_base_dir.iterdir()
                if path.is_file() and path.suffix.casefold() == ".pdf"
            ),
            key=lambda path: path.name.casefold(),
        )
        if knowledge_base_dir.is_dir()
        else []
    )
    if len(pdf_files) != KnowledgeBaseIngestionService.EXPECTED_PDF_COUNT:
        raise KnowledgeBaseConfigurationError(
            "--recreate requires exactly 3 PDFs before clearing Qdrant"
        )

    contents = [path.read_bytes() for path in pdf_files]
    checksums = [hashlib.sha256(content).hexdigest() for content in contents]
    if len(set(checksums)) != len(checksums):
        raise KnowledgeBaseConfigurationError(
            "--recreate refused because duplicate PDF content was detected"
        )

    loader = PyPDFTextLoader()
    for path, content in zip(pdf_files, contents, strict=True):
        loader.load(content, path.name)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Index the fixed trusted PDF knowledge base.",
    )
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Delete and recreate the Qdrant collection before indexing.",
    )
    arguments = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO)
    try:
        return asyncio.run(ingest(recreate=arguments.recreate))
    except (KnowledgeBaseError, DocumentValidationError) as error:
        print(f"Knowledge base ingestion failed: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
