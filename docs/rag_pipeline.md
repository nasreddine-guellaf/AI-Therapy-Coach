# Fixed knowledge-base RAG pipeline

The assistant uses exactly three trusted PDFs selected by the project owner.
Users cannot upload documents. The owner or an authorized administrator indexes
the files locally before the application is used.

```text
3 trusted PDFs in backend/data/knowledge_base
  -> admin ingestion script
  -> page-level text extraction
  -> page-aware chunking
  -> multilingual E5-small embeddings
  -> global Qdrant collection: therapy_knowledge_chunks

Authenticated conversation
  -> query embedding
  -> global cosine retrieval (top 4 by default)
  -> structured chunks in PromptBuilder
  -> LLM answer with source metadata
```

## Prepare and ingest the knowledge base

Place exactly three `.pdf` files in `backend/data/knowledge_base/`. Only PDFs
with a selectable text layer are supported. Scanned or image-only files fail
with:

```text
No extractable text found. OCR is not supported yet.
```

PDF binaries are ignored by Git. Commit them only when their licenses allow
redistribution.

Start Qdrant from the repository root, then run the script from `backend`:

```powershell
docker compose up -d qdrant
cd backend
python -m app.scripts.ingest_knowledge_base
```

The script fails when the directory is missing or contains no PDFs and warns
when the number of PDFs is not exactly three.

## Idempotency and metadata

Document IDs are deterministic from normalized filenames. Point/source IDs are
deterministic from filename, page number, and chunk index. Before upserting one
document, the adapter removes its previous points, preventing duplicate or
stale chunks when the script is run again.

Each Qdrant payload contains:

- `document_id`
- `filename`
- `source_id`
- `page_number`
- `chunk_index`
- `text`
- `created_at`

There is no `user_id` payload or tenant filter. The collection is a shared,
owner-curated knowledge base.

## Extraction, chunking, and embeddings

`PyPDFTextLoader` uses `pypdf` and retains one-based page numbers.
`TextChunker` keeps chunks within a page and defaults to 1,000 characters with
150 characters of overlap.

`LocalE5EmbeddingProvider` lazily loads
`intfloat/multilingual-e5-small`, applies `passage:` and `query:` prefixes,
normalizes vectors, and enforces 384 dimensions. The first run downloads the
model weights.

## Retrieval and prompt grounding

Every ordinary conversation turn queries `therapy_knowledge_chunks`.
`RAG_TOP_K` defaults to four. Retrieved chunks and their explicit metadata are
injected into the existing `RETRIEVED RAG CONTEXT` prompt section.

The prompt requires the model to use retrieved context as the primary source
for document-grounded claims, never invent missing content or citations, and
state when the evidence is insufficient. General coaching guidance remains
available when appropriate. If Qdrant is unavailable or returns no chunks, the
conversation continues safely with an empty RAG context.

Sources are returned in the API response and persisted in assistant-message
metadata so they remain visible when a conversation is reopened.

## Configuration

```env
KNOWLEDGE_BASE_DIR=backend/data/knowledge_base
RAG_COLLECTION_NAME=therapy_knowledge_chunks
RAG_TOP_K=4
EMBEDDING_PROVIDER=local
EMBEDDING_MODEL=intfloat/multilingual-e5-small
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
```

## Current limitations

- exactly one owner-managed knowledge base and embedding model;
- no OCR, scanned-PDF processing, malware scanning, or licensing checks;
- no background ingestion queue or admin dashboard;
- no reranking, score threshold, or automated citation verification;
- reindexing is per document rather than an atomic collection-wide release;
- filename changes create a new document identity, so administrators should
  remove obsolete points or recreate the collection when renaming sources.
