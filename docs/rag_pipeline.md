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
when the number of PDFs is not exactly three. Use a full rebuild only after all
three files are present:

```powershell
python -m app.scripts.ingest_knowledge_base --recreate
```

`--recreate` deletes and recreates the configured Qdrant collection before
indexing. Before deletion, it verifies that exactly three distinct PDFs are
present and that each has extractable text.

## Idempotency and metadata

Document IDs are deterministic from normalized filenames. Point/source IDs are
deterministic from filename, page number, and chunk index. Before upserting one
document, the adapter removes its previous points, preventing duplicate or
stale chunks when the script is run again.

After a successful complete run, the script atomically writes the ignored
`manifest.json`. It contains filename, SHA-256 checksum, indexing timestamp,
chunk count, embedding model, and collection name, but never document text.
Duplicate PDF content is rejected. Changed checksums and files missing since the
previous manifest are logged clearly without logging their contents.

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
`RAG_TOP_K` defaults to four. The adapter requests additional candidates, drops
scores below `RAG_MIN_SCORE` (default `0.25`), removes exact and near-duplicate
text while retaining the highest score, and injects at most `RAG_TOP_K` chunks
into the existing `RETRIEVED RAG CONTEXT` prompt section.

Questions explicitly asking what the documents say use
`RAG_DOCUMENT_QUESTION_MIN_SCORE` (default `0.35`). Weak chunks are excluded
from the prompt and from API sources. The LLM still receives the conversation
with `availability=none`, so it can offer safe general coaching while clearly
disclosing that the documents are insufficient.

The prompt requires the model to distinguish document-grounded claims from
general guidance, never invent missing content or citations, and never claim
document support when context is empty. If Qdrant is unavailable or returns no
chunks, the conversation continues safely with an empty RAG context.

Sources are returned in the API response and persisted in assistant-message
metadata so they remain visible when a conversation is reopened.

Safe structured logs contain only retrieval latency, candidate counts,
post-threshold and post-deduplication counts, whether thresholding removed all
candidates, and provider error types. Questions, prompts, document text,
conversation content, and credentials are never logged.

## Reliability evaluation

`backend/evaluations/rag/dataset.json` contains 30 answerable,
cross-document, unanswerable, multilingual, and safety cases. The runner tests
retrieval and rule-based safety without invoking the LLM:

```powershell
cd backend
python -m app.scripts.evaluate_rag
python -m app.scripts.evaluate_rag --output evaluations/rag/latest_results.json
```

Reports include per-chunk scores, maximum/minimum/average retrieval score,
accepted-versus-rejected chunk counts, and category scores. An unanswerable
case passes when no document source is accepted; generation is expected to use
the safe general-fallback mode rather than return no answer.

Once questions and source IDs have been curated against the final licensed
PDFs, CI can use `--fail-on-mismatch`.

## Readiness

Authenticated clients can inspect safe collection aggregates:

```http
GET /api/rag/readiness
Authorization: Bearer <access_token>
```

Readiness is `ready` only when Qdrant is reachable, the collection exists,
exactly three distinct document IDs are indexed, and at least one chunk exists.
No filename, source text, vector, prompt, or user content is returned.

## Configuration

```env
KNOWLEDGE_BASE_DIR=backend/data/knowledge_base
RAG_COLLECTION_NAME=therapy_knowledge_chunks
RAG_TOP_K=4
RAG_MIN_SCORE=0.25
RAG_DOCUMENT_QUESTION_MIN_SCORE=0.35
EMBEDDING_PROVIDER=local
EMBEDDING_MODEL=intfloat/multilingual-e5-small
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
```

## Current limitations

- exactly one owner-managed knowledge base and embedding model;
- no OCR, scanned-PDF processing, malware scanning, or licensing checks;
- no background ingestion queue or admin dashboard;
- no reranking or automated citation verification;
- reindexing is per document rather than an atomic collection-wide release;
- filename changes create a new document identity, so administrators should
  remove obsolete points or recreate the collection when renaming sources.
