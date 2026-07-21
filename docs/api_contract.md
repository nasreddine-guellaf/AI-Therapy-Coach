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
| `session_id` | string or null | No | Reserved for persisted memory |

### Response

HTTP `202 Accepted`:

```json
{
  "message": "What is one small task that would make today feel lighter?",
  "status": "completed",
  "memory_items_used": 0,
  "rag_chunks_used": 0,
  "source_ids": []
}
```

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

The current RAG retriever and memory service return empty context. Their counts
and `source_ids` remain part of the stable response for future integration.

## `POST /api/documents/upload`

Multipart request with a `file` field. Current response:

```json
{ "filename": "document.pdf", "status": "pending" }
```

Validation and asynchronous ingestion remain to be implemented.

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
