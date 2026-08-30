# API contract

All routes use the `/api` prefix. Clients must not treat conversation output as
medical advice. Protected endpoints require:

```http
Authorization: Bearer <access_token>
```

## `POST /api/auth/register`

Creates an account from `email`, `password`, and optional `full_name`. It
returns HTTP `201` with basic user information and never returns the password
hash. A duplicate email returns HTTP `409`.

## `POST /api/auth/login`

Accepts `email` and `password`, then returns a signed JWT and basic user data:

```json
{
  "access_token": "signed-jwt",
  "token_type": "bearer",
  "user": {
    "id": "user-uuid",
    "email": "person@example.com",
    "full_name": "Optional Name",
    "is_active": true,
    "created_at": "2026-07-18T20:00:00Z"
  }
}
```

Invalid credentials return the same HTTP `401` response whether the email or
password was incorrect.

## `GET /api/auth/me`

Requires a Bearer token and returns the current active user. Missing, invalid,
or expired tokens return HTTP `401`.

## `POST /api/conversation/message`

Runs one safe text conversation turn.

Provider routing does not change this public contract. When Gemini is selected
and reaches its rate limit, the backend may retry through the configured
OpenRouter fallback. If both providers are unavailable, the endpoint returns
the existing safe `llm_unavailable` status without raw provider details.

This endpoint requires a valid Bearer token. `user_id` is never accepted from
the request; the backend derives it from the signed JWT subject.

### Request

```json
{
  "message": "I feel overwhelmed and need a small next step",
  "session_id": "optional-session-id"
}
```

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `message` | string | Yes | 1–5,000 characters |
| `session_id` | UUID or null | No | Omit to create a session; reuse the returned ID for later turns |

### Response

HTTP `202 Accepted`:

```json
{
  "message": "What is one small task that would make today feel lighter?",
  "status": "completed",
  "session_id": "10000000-0000-0000-0000-000000000001",
  "memory_items_used": 4,
  "rag_chunks_used": 0,
  "rag_availability": "none",
  "source_ids": [],
  "sources": []
}
```

The backend stores the user turn first, loads up to the eight preceding turns
from the same session, injects them into `CONVERSATION HISTORY`, and stores the
validated assistant turn. A supplied session must belong to the JWT user;
missing and foreign sessions both return HTTP `404`. Storage failures return a
safe HTTP `503` without database details.

Current status values:

| Status | Meaning |
| --- | --- |
| `completed` | Provider output passed response validation |
| `escalation_required` | Critical rule matched; no LLM call was made |
| `validation_failed` | Generated text failed scope/safety validation |
| `llm_unavailable` | Missing key, timeout, connection, authentication, rate-limit, provider API, or empty-output failure |

When the selected provider key is absent, the endpoint returns a safe
`llm_unavailable` response rather than raising a server error. The server never
returns API keys, provider exception details, JWT signing secrets, password
hashes, or rejected model text.

Supported provider selections are `openai`, `openrouter`, and `gemini` through
`LLM_PROVIDER`. Gemini uses its OpenAI-compatible Chat Completions endpoint.
Provider selection does not change this public response contract. There is no
automatic fallback between providers in this version.

`memory_items_used` counts prior turns supplied to the prompt. Every ordinary
turn retrieves up to `RAG_TOP_K` chunks from the global, fixed internal
knowledge base. When chunks are available, `sources` contains `source_id`,
`filename`, `page_number`, `chunk_index`, and similarity `score`.
Candidates below `RAG_MIN_SCORE` are removed and near-duplicate chunks are
collapsed before prompt construction. If no candidates remain,
`rag_chunks_used` is `0`, `source_ids` and `sources` are empty, and
`PromptBuilder` receives `availability=none`. The LLM is still called for safe
general coaching unless `SafetyService` requires immediate escalation.

Explicit document questions use the stricter
`RAG_DOCUMENT_QUESTION_MIN_SCORE`. When no chunk passes it, the response first
states that the documents are insufficient, then may provide clearly separated
general non-medical guidance. `rag_availability` is `provided` only when chunks
were injected; otherwise it is `none`. Sources are never attached to fallback
guidance.

Sources are returned only when `status` is `completed`. Provider failures,
validation failures, and Gemini truncation after one retry return empty
`source_ids` and `sources`. Gemini truncation uses status `llm_incomplete`; its
partial content is never stored as an assistant message.

The knowledge base consists of three trusted PDFs selected by the project
owner. Users do not upload PDFs and no document-upload endpoint is part of the
public API. An administrator indexes the files with:

```powershell
python -m app.scripts.ingest_knowledge_base
```

## `GET /api/rag/readiness`

Requires a Bearer token and returns safe operational aggregates:

```json
{
  "qdrant_reachable": true,
  "collection_exists": true,
  "indexed_document_count": 3,
  "total_chunk_count": 42,
  "expected_pdf_count": 3,
  "embedding_model": "intfloat/multilingual-e5-small",
  "status": "ready"
}
```

`status` is `ready` only when Qdrant is reachable, the collection exists,
exactly three distinct documents are indexed, and the collection contains at
least one chunk. The endpoint never returns filenames, chunks, vectors, prompts,
credentials, or conversation content. Qdrant failures produce a safe
`not_ready` payload rather than raw infrastructure errors.

## `GET /api/conversations`

Returns at most 50 sessions owned by the authenticated user, ordered by most
recently updated first:

```json
[
  {
    "session_id": "10000000-0000-0000-0000-000000000001",
    "title": "I feel overwhelmed",
    "created_at": "2026-07-21T09:00:00Z",
    "updated_at": "2026-07-21T09:05:00Z",
    "last_message_preview": "What is one task that can wait?"
  }
]
```

The owner is always taken from the JWT. No `user_id` query or response field is
supported.

## `GET /api/conversations/{session_id}`

Returns owned session metadata and messages ordered from oldest to newest:

```json
{
  "session_id": "10000000-0000-0000-0000-000000000001",
  "title": "I feel overwhelmed",
  "created_at": "2026-07-21T09:00:00Z",
  "updated_at": "2026-07-21T09:05:00Z",
  "messages": [
    {
      "id": "message-uuid",
      "role": "user",
      "content": "I feel overwhelmed",
      "metadata": null,
      "created_at": "2026-07-21T09:00:00Z"
    }
  ]
}
```

A missing or foreign session returns the same HTTP `404` response.

## `DELETE /api/conversations/{session_id}`

Permanently deletes an owned session and its messages through the database
cascade, returning HTTP `204 No Content`. This MVP uses hard deletion; advanced
retention and recovery policies remain production work. Missing and foreign
sessions return HTTP `404`.

## `POST /api/voice/transcribe`

Reserved for audio upload and speech-to-text. Currently returns HTTP `501` and
makes no Whisper call.

## `POST /api/voice/synthesize`

Reserved for text-to-speech. Currently returns HTTP `501` and makes no
ElevenLabs call.

## `GET /api/health`

HTTP `200`:

```json
{
  "status": "ok",
  "service": "AI Therapy Coach Backend"
}
```

This is a liveness endpoint and does not call PostgreSQL, OpenAI, or Qdrant.

History endpoints return HTTP `503` with a generic message when persistence is
unavailable. Raw SQL, connection strings, and database errors are never exposed.
