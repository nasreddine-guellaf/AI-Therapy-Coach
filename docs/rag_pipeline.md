# Retrieval-Augmented Generation pipeline

This first version defines the local RAG structure without connecting to OpenAI
or Qdrant. Every external capability is injected behind an interface so the
pipeline can be tested with deterministic local doubles.

## Target flow

```text
PDF bytes
   ↓
PDFLoader → LoadedPage[]
   ↓
TextChunker → TextChunk[]
   ↓
EmbeddingProvider.embed_documents(...)
   ↓
VectorStore.upsert(...) → future Qdrant adapter

User query
   ↓
EmbeddingProvider.embed_query(...)
   ↓
VectorStore.search(...)
   ↓
Retriever.retrieve_relevant_chunks(query, top_k)
   ↓
Prompt Builder → LLM → validation and safety guardrails
```

## Components

### PDF loading

`PDFLoader` is an abstract contract that converts PDF bytes into ordered
`LoadedPage` values. Each page contains extracted text, its one-based page
number, and source metadata. `PlaceholderPDFLoader` currently validates empty
payloads and the PDF signature, then stops explicitly because no parser has been
selected.

A production loader must add:

- file-size and page-count limits;
- MIME and PDF-signature validation;
- malware scanning and sandboxed parsing;
- encrypted/corrupt PDF handling;
- OCR fallback and extraction-quality metrics;
- source checksum and document identifier metadata.

### Chunking

`TextChunker` implements deterministic character-based chunks with configurable
size and overlap. Pages are chunked independently so a citation never crosses a
page boundary. Every `TextChunk` retains:

- page number;
- global chunk index;
- start/end character offsets;
- inherited document metadata.

The default is 1,000 characters with 150 characters of overlap. Once an
embedding model is selected, tokenizer-aware and semantic splitting should be
evaluated instead of assuming characters map consistently to tokens.

### Embeddings

`EmbeddingProvider` defines separate asynchronous methods for documents and
queries. No provider SDK is imported. `DeterministicMockEmbeddingProvider`
produces stable, non-semantic vectors for unit tests only; it must never be used
for production relevance decisions.

The future OpenAI adapter should implement batching, rate-limit handling,
timeouts, retry/backoff, dimension checks, model/version metadata, cost metrics,
and secret redaction.

### Vector storage

The domain-level `VectorStore` port exposes provider-neutral `upsert` and
`search` methods. `QdrantVectorStore` stores configuration but intentionally
raises `NotImplementedError` before any network call. Its future implementation
will use the async Qdrant client and must add:

- idempotent collection setup and dimension validation;
- payload indexes and authorization/tenant filters;
- document deletion propagation;
- request timeouts, retry policy, and telemetry;
- safeguards preventing sensitive message history from becoming payload data.

No API keys are stored in code. `QDRANT_URL` and `QDRANT_API_KEY` remain
environment settings.

### Retrieval

`Retriever.retrieve_relevant_chunks(query, top_k)` validates the request,
embeds the query through `EmbeddingProvider`, searches through `VectorStore`,
and maps provider results into `RetrievedChunk` values. Payloads without usable
text are ignored.

Future work includes score thresholds, user/document authorization filters,
deduplication, hybrid search, reranking, citation validation, and retrieval
quality evaluation. Retrieved content must still pass prompt-boundary and safety
controls; RAG evidence is not automatically trustworthy or medically valid.

## Current limitations

- No real PDF parser is configured.
- No OpenAI embedding request is made.
- No Qdrant request is made.
- Ingestion orchestration and persistence status updates are not implemented.
- No prompt builder or LLM is invoked by this pipeline version.

These limitations are deliberate: this version establishes clean contracts and
testable local behavior before external integrations are enabled.
