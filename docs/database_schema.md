# PostgreSQL database schema

PostgreSQL is the relational source of truth for user ownership, coaching
sessions, messages, document metadata, and explicit conversational memory.
Qdrant remains responsible only for vector chunks and minimal retrieval
metadata. File binaries are not stored in PostgreSQL.

The SQLAlchemy mappings live in
`backend/app/infrastructure/database/models.py`; domain entities remain free of
persistence concerns. All identifiers are UUIDs so they can safely cross API and
service boundaries. Timestamps use timezone-aware PostgreSQL values.

## Tables

### `users`

Purpose: minimal owner profile, ready to be linked to a future authentication
identity without storing credentials now.

| Field | Type | Rules | Purpose |
| --- | --- | --- | --- |
| `id` | UUID | Primary key | Public-safe user identifier |
| `display_name` | VARCHAR(120) | Required | Non-authentication display label |
| `is_active` | BOOLEAN | Required, defaults to true | Future soft account disabling |
| `created_at` | TIMESTAMPTZ | Required, server default | Creation audit time |
| `updated_at` | TIMESTAMPTZ | Required, server managed | Last update time |

No email, password, token, or API key is stored. Authentication can later add a
separate identity table or an external provider identifier.

### `coaching_sessions`

Purpose: one bounded coaching conversation for a user.

| Field | Type | Rules | Purpose |
| --- | --- | --- | --- |
| `id` | UUID | Primary key | Session identifier |
| `user_id` | UUID | FK → `users.id`, required | Session owner |
| `status` | VARCHAR(20) | `active`, `completed`, or `archived` | Lifecycle state |
| `started_at` | TIMESTAMPTZ | Required, server default | Conversation start |
| `ended_at` | TIMESTAMPTZ | Optional | Conversation end |
| `created_at` | TIMESTAMPTZ | Required | Creation audit time |
| `updated_at` | TIMESTAMPTZ | Required | Last update time |

`(user_id, created_at)` is indexed for user history queries. Deleting a user
cascades to their sessions.

### `messages`

Purpose: ordered conversation turns within a coaching session.

| Field | Type | Rules | Purpose |
| --- | --- | --- | --- |
| `id` | UUID | Primary key | Message identifier |
| `session_id` | UUID | FK → `coaching_sessions.id`, required | Parent session |
| `role` | VARCHAR(20) | `user`, `assistant`, or `system` | Message author type |
| `content` | TEXT | Required | Message body |
| `created_at` | TIMESTAMPTZ | Required | Ordering and audit time |
| `updated_at` | TIMESTAMPTZ | Required | Correction/audit support |

`(session_id, created_at)` is indexed for chronological retrieval. Deleting a
session deletes its messages. Sensitive message content must be protected by
access controls, retention rules, and encryption in production.

### `documents`

Purpose: ingestion metadata for RAG documents. The actual PDF belongs in object
storage; chunks and embeddings belong in Qdrant.

| Field | Type | Rules | Purpose |
| --- | --- | --- | --- |
| `id` | UUID | Primary key | Document identifier |
| `user_id` | UUID | Optional FK → `users.id` | Optional uploader/owner |
| `filename` | VARCHAR(255) | Required | Original display name |
| `storage_key` | TEXT | Optional, unique | Object-storage reference |
| `content_type` | VARCHAR(100) | Defaults to `application/pdf` | Validated media type |
| `checksum` | VARCHAR(64) | Optional, indexed | Deduplication/integrity aid |
| `status` | VARCHAR(20) | `pending`, `processing`, `ready`, or `failed` | Ingestion state |
| `created_at` | TIMESTAMPTZ | Required | Creation audit time |
| `updated_at` | TIMESTAMPTZ | Required | Last state change |

Deleting a user sets `user_id` to null rather than deleting shared or curated
knowledge. `(user_id, created_at)` supports owner-scoped document listings.

### `memory_entries`

Purpose: explicit, reviewable memory facts that may be reused in future
conversations. It is deliberately separate from raw message history.

| Field | Type | Rules | Purpose |
| --- | --- | --- | --- |
| `id` | UUID | Primary key | Memory identifier |
| `user_id` | UUID | FK → `users.id`, required | Memory owner |
| `session_id` | UUID | Optional FK → `coaching_sessions.id` | Originating session |
| `source_message_id` | UUID | Optional FK → `messages.id` | Traceable source message |
| `category` | VARCHAR(50) | Required, defaults to `general` | Future retrieval grouping |
| `content` | TEXT | Required | Concise retained fact |
| `is_active` | BOOLEAN | Required, defaults to true | Revocation/soft deletion |
| `expires_at` | TIMESTAMPTZ | Optional | Retention boundary |
| `created_at` | TIMESTAMPTZ | Required | Creation audit time |
| `updated_at` | TIMESTAMPTZ | Required | Last update time |

Foreign-key and `(user_id, is_active)` indexes support active-memory retrieval.
Deleting a user deletes their memory. Deleting a source session or message keeps
the memory but nulls the provenance link, allowing retention policy to decide
whether it should subsequently be removed.

## Relationships

```text
users 1 ─── * coaching_sessions 1 ─── * messages
  │                   │                    │
  │                   └── * memory_entries ┘ (optional provenance)
  ├── * memory_entries
  └── * documents (optional ownership)
```

## Design rationale

- Persistence models are separate from domain entities to preserve the current
  clean/hexagonal architecture.
- UUIDs match the existing domain and are suitable for externally visible IDs.
  A time-ordered UUID strategy can be adopted later if write volume requires it.
- PostgreSQL `TIMESTAMPTZ` avoids ambiguous local times.
- Check constraints prevent invalid role and status values without tying the
  schema to PostgreSQL-native enums, which keeps migrations simpler.
- Every foreign-key access path is indexed, either directly or as the leading
  column of a composite index.
- Database sessions use SQLAlchemy's async pool; `DATABASE_URL` is loaded from
  environment settings and must use the `postgresql+asyncpg://` driver.
- Memory expiration, activation, and provenance prepare for future consent,
  correction, deletion, and retention workflows.
- Alembic migrations, row-level authorization, encryption strategy, and full
  repositories/CRUD are intentionally deferred.
