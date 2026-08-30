# AI Therapy Coach Backend

FastAPI backend for a non-medical conversational coaching prototype. The text
conversation flow uses a provider-neutral `LLMProvider`; the infrastructure
adapters support OpenAI Responses, OpenRouter Chat Completions, and Gemini's
OpenAI-compatible Chat Completions endpoint. Only the provider selected by
`LLM_PROVIDER` is used. RAG uses three fixed, trusted PDFs maintained by the
project owner; users cannot upload documents. Voice and avatar remain disabled
placeholders.

## Requirements

- Python 3.12+
- `pip`
- PostgreSQL 16+ or Docker Desktop
- An API key for the selected LLM provider only when testing real responses

## Install and run locally

From the `backend` directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

On macOS or Linux, activate with `source .venv/bin/activate` and use the same
Python commands.

Open:

- Health: <http://127.0.0.1:8000/api/health>
- Swagger UI: <http://127.0.0.1:8000/docs>
- ReDoc: <http://127.0.0.1:8000/redoc>

## PostgreSQL and authentication setup

Start PostgreSQL from the repository root:

```powershell
docker compose up -d postgres
```

When running the full Docker Compose stack, migrate before starting the API:

```powershell
docker compose up -d postgres
docker compose run --rm backend python -m alembic upgrade head
docker compose up -d backend frontend
```

When running FastAPI directly on the host, configure `backend/.env`:

```env
DATABASE_URL=postgresql+asyncpg://therapeutic:therapeutic@localhost:5433/therapeutic_ai
DATABASE_CONNECT_TIMEOUT_SECONDS=5
SECRET_KEY=replace-with-a-random-secret-of-at-least-32-characters
ACCESS_TOKEN_EXPIRE_MINUTES=30
APP_ENV=development
```

Generate a local signing secret without committing it:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

FastAPI never creates or modifies the schema during startup. Alembic is the
only schema-management mechanism.

Docker exposes PostgreSQL on host port `5433` to avoid conflicts with local
PostgreSQL installations or stale Docker port proxies. Containers still connect
to `postgres:5432`; Docker Compose supplies that internal URL to the backend.

### Run database migrations

From `backend`, with `DATABASE_URL` configured:

```powershell
python -m alembic upgrade head
python -m alembic current
```

For a database already created by the pre-Alembic MVP, first back it up and
verify that it contains the schema documented in `docs/database_schema.md`.
Then adopt the baseline and apply the history index migration:

```powershell
python -m alembic stamp 20260721_0001
python -m alembic upgrade head
```

Do not run `stamp` on an empty database: it records a revision without creating
tables. Fresh databases must use `upgrade head` directly.

After changing SQLAlchemy models, create and review a new migration:

```powershell
python -m alembic revision --autogenerate -m "describe schema change"
python -m alembic upgrade head
```

Review generated upgrade and downgrade operations before applying them. In a
deployment, run migrations as a separate release step before starting FastAPI.

If `alembic upgrade head` reports a connection or authentication failure,
verify the ignored `backend/.env` and the local PostgreSQL role/database. FastAPI
startup intentionally does not test or mutate the schema; database-backed
endpoints return safe service-unavailable responses when persistence cannot be
reached. Connection URLs and passwords are never written to application logs.

Register and login:

```powershell
$registration = @{
  email = "person@example.com"
  password = "a-local-password-123"
  full_name = "Test Person"
} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/auth/register `
  -ContentType "application/json" -Body $registration

$login = @{ email = "person@example.com"; password = "a-local-password-123" } |
  ConvertTo-Json
$auth = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/auth/login `
  -ContentType "application/json" -Body $login
```

Passwords are hashed with Argon2. Plaintext passwords, signing secrets, and
access tokens are never stored in PostgreSQL.

## LLM provider configuration

Copy the repository `.env.example` to `.env`. OpenAI remains the default:

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-5.6-luna
OPENAI_TIMEOUT_SECONDS=30
OPENAI_MAX_OUTPUT_TOKENS=700
```

To use OpenRouter instead:

```env
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=your_key_here
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=qwen/qwen3-next-80b-a3b-instruct:free
```

To use Google Gemini through its OpenAI-compatible endpoint:

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_key_here
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
GEMINI_MODEL=gemini-3.7-flash
GEMINI_MAX_OUTPUT_TOKENS=1200
```

Never commit `.env` or expose any provider key to the frontend. The backend reads the
selected credential from environment settings and passes it only to that
provider's infrastructure adapter. It never returns prompts, keys, or raw SDK
errors in API responses.

`OPENAI_MODEL` is configurable so deployments can select an available model
without changing domain code. The initial default uses a cost-sensitive text
model. Before production, pin a tested model snapshot and maintain prompt evals.

The adapter follows OpenAI's current recommendation to use the Responses API for
new text-generation applications:

- <https://developers.openai.com/api/docs/guides/text>
- <https://developers.openai.com/api/docs/guides/error-codes>

The OpenRouter and Gemini adapters use OpenAI-compatible Chat Completions via
`client.chat.completions.create`; they do not use the Responses API. The
application does not automatically fall back between providers: selection is
explicit and deterministic through `LLM_PROVIDER`.

The Gemini adapter sends `GEMINI_MAX_OUTPUT_TOKENS` as
`max_completion_tokens`. If Gemini ends with `finish_reason=length`, the
adapter retries once with twice that limit. A second truncation returns
`llm_incomplete`; the partial text is neither persisted nor attributed to RAG
sources. Logs contain only provider/model, finish reason, empty-content state,
output token count when supplied, and error type—never prompts or response text.

OpenRouter references:

- <https://openrouter.ai/docs/quickstart>
- <https://openrouter.ai/docs/guides/community/openai-sdk>

## Fixed knowledge-base RAG

Place exactly three trusted, text-based PDFs in:

```text
backend/data/knowledge_base/
```

PDFs in this directory are ignored by Git. Do not commit real files unless
their license permits redistribution. OCR and scanned-only PDFs are not
supported.

Start Qdrant from the repository root and run the administrative ingestion:

```powershell
docker compose up -d qdrant
cd backend
python -m app.scripts.ingest_knowledge_base
```

To clear and rebuild the complete collection:

```powershell
python -m app.scripts.ingest_knowledge_base --recreate
```

The destructive mode validates that exactly three distinct PDFs are present and
that each has extractable text before it clears Qdrant.

Use these settings when the backend runs directly on the host:

```env
KNOWLEDGE_BASE_DIR=backend/data/knowledge_base
RAG_COLLECTION_NAME=therapy_knowledge_chunks
RAG_TOP_K=4
RAG_MIN_SCORE=0.25
RAG_DOCUMENT_QUESTION_MIN_SCORE=0.35
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
EMBEDDING_PROVIDER=local
EMBEDDING_MODEL=intfloat/multilingual-e5-small
```

The script warns if the directory does not contain exactly three PDFs and fails
if the directory is missing, contains no PDFs, contains duplicate PDF content,
or a PDF has no extractable text. It creates the global
`therapy_knowledge_chunks` collection and replaces each document's existing
points using stable IDs, so rerunning it does not duplicate chunks.

A successful run generates ignored
`backend/data/knowledge_base/manifest.json` with checksums, indexing timestamps,
chunk counts, embedding model, and collection name. Document text is excluded.
The script reports changed checksums and files missing since the prior manifest.

The local model is downloaded on the first ingestion or RAG query. It produces
384-dimensional normalized embeddings and may take several minutes on first
use. Docker Compose preserves the Hugging Face cache in a named volume.

There is no public document-upload API. Authentication still protects coaching
conversations and their PostgreSQL history, but retrieval reads the same trusted
knowledge collection for every authenticated user.

Retrieval drops candidates below `RAG_MIN_SCORE`, removes exact and
near-duplicate chunks while retaining the highest-scoring one, and returns at
most `RAG_TOP_K` sources. Safe logs include only latency, counts, threshold
outcomes, and error types.

Explicit document questions additionally require
`RAG_DOCUMENT_QUESTION_MIN_SCORE` (default `0.35`). If no chunk passes, the LLM
still provides safe general coaching where appropriate, prefixed by a clear
document-insufficiency notice. The response reports `rag_availability=none`
and returns no sources. Medical requests are refused and crisis messages still
short-circuit through `SafetyService`.

### Run the RAG evaluation

The 30-case baseline measures retrieval and safety without calling the LLM. It
reports per-chunk and aggregate similarity scores plus scores by category:

```powershell
python -m app.scripts.evaluate_rag
python -m app.scripts.evaluate_rag `
  --output evaluations/rag/latest_results.json
```

After curating exact source IDs for the final three PDFs, use
`--fail-on-mismatch` in CI.

### Check RAG readiness

With an authenticated token:

```powershell
Invoke-RestMethod `
  -Method Get `
  -Uri http://127.0.0.1:8000/api/rag/readiness `
  -Headers @{ Authorization = "Bearer $($auth.access_token)" }
```

The response reports Qdrant reachability, collection presence, distinct indexed
document count, total chunk count, expected count, model, and `ready` or
`not_ready`. It never returns source text.

## Test the conversation endpoint

With the backend running:

```powershell
$body = @{ message = "I feel overwhelmed and need a small next step" } |
  ConvertTo-Json
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/api/conversation/message `
  -ContentType "application/json" `
  -Headers @{ Authorization = "Bearer $($auth.access_token)" } `
  -Body $body
```

The response contains `session_id`. Send it with the next turn to reuse the
same recent history:

```powershell
$first = Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/api/conversation/message `
  -ContentType "application/json" `
  -Headers @{ Authorization = "Bearer $($auth.access_token)" } `
  -Body (@{ message = "I feel overwhelmed" } | ConvertTo-Json)

$second = @{ message = "What did I just tell you?"; session_id = $first.session_id } |
  ConvertTo-Json
Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/api/conversation/message `
  -ContentType "application/json" `
  -Headers @{ Authorization = "Bearer $($auth.access_token)" } `
  -Body $second
```

If the selected provider's API key is missing, the endpoint still returns HTTP
`202` with status `llm_unavailable` and a clean configuration message. No
external request is attempted. With a valid key, the selected adapter generates
a response, then the domain `ResponseValidator` checks it before it reaches the
frontend. A Gemini response that remains truncated after the single retry uses
status `llm_incomplete`, contains no partial generated text or sources, and is
not stored as an assistant turn.

## Architecture flow

```text
FastAPI route
  → ConversationManager
  → SafetyService
  → ConversationSessionRepository / MessageRepository
  → PostgreSQL adapters (store user turn, load up to 8 prior turns)
  → global fixed-knowledge E5/Qdrant retriever
  → PromptBuilder
  → LLMProvider
  → OpenAILLMProvider (Responses API), or
    OpenRouterLLMProvider (Chat Completions API), or
    GeminiLLMProvider (OpenAI-compatible Chat Completions API)
  → ResponseValidator
  → PostgreSQL adapter (store validated assistant turn)
  → structured API response
```

Routes and domain services do not import or instantiate the OpenAI SDK. Provider
selection and adapter wiring live in `app/api/dependencies.py`.

Conversation history is exposed through authenticated `GET /api/conversations`,
`GET /api/conversations/{session_id}`, and
`DELETE /api/conversations/{session_id}` endpoints. Repository queries always
include the JWT user's ID; a foreign session returns the same `404` as a missing
session.

## Tests

```powershell
python -m pytest -q
```

Unit tests inject fake LLM, embedding, and Qdrant adapters and make no real
OpenAI, OpenRouter, or Gemini request.

## Production TODOs

- Define and enforce a conversation retention policy.
- Add authenticated user data deletion and export workflows.
- Establish an encryption strategy for sensitive message content.
- Add idempotency keys so retried message deliveries cannot create duplicates.
- Add cursor pagination before conversation histories can grow beyond the
  current bounded list.

## Other configuration

CORS allows `http://localhost:3000` by default. Override it with a JSON array:

```env
CORS_ORIGINS=["http://localhost:3000","http://127.0.0.1:3000"]
```
