# AI Therapy Coach Backend

FastAPI backend for a non-medical conversational coaching prototype. The text
conversation flow uses a provider-neutral `LLMProvider`; the infrastructure
adapters support OpenAI Responses and OpenRouter Chat Completions. Only the
provider selected by `LLM_PROVIDER` is used. Qdrant, voice, and avatar
integrations remain disabled placeholders.

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

When running FastAPI directly on the host, configure `backend/.env`:

```env
DATABASE_URL=postgresql+asyncpg://therapeutic:therapeutic@localhost:5432/therapeutic_ai
DATABASE_AUTO_CREATE=true
DATABASE_CONNECT_TIMEOUT_SECONDS=5
SECRET_KEY=replace-with-a-random-secret-of-at-least-32-characters
ACCESS_TOKEN_EXPIRE_MINUTES=30
APP_ENV=development
```

Generate a local signing secret without committing it:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

The MVP creates missing tables on startup. `create_all` does not migrate an
already-existing `users` table; use Alembic migrations for upgrades and set
`DATABASE_AUTO_CREATE=false` in production.

If startup logs `cause_type=InvalidPasswordError`, PostgreSQL is reachable but
the credentials in `DATABASE_URL` do not match the running server. Update only
your ignored `backend/.env` with the actual local PostgreSQL role/password, or
create the documented `therapeutic` role and database. The API remains available
for liveness checks, but registration, login, and `/auth/me` return a safe
service-unavailable response until the database credentials work. Connection
URLs and passwords are never written to logs.

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

Never commit `.env` or expose either key to the frontend. The backend reads the
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

The OpenRouter adapter uses the OpenAI-compatible Chat Completions endpoint via
`client.chat.completions.create`; it does not use the Responses API:

- <https://openrouter.ai/docs/quickstart>
- <https://openrouter.ai/docs/guides/community/openai-sdk>

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

If the selected provider's API key is missing, the endpoint still returns HTTP
`202` with status `llm_unavailable` and a clean configuration message. No
external request is attempted. With a valid key, the selected adapter generates
a response, then the domain `ResponseValidator` checks it before it reaches the
frontend.

## Architecture flow

```text
FastAPI route
  → ConversationManager
  → SafetyService
  → MemoryService / empty RAG adapter
  → PromptBuilder
  → LLMProvider
  → OpenAILLMProvider (Responses API), or
    OpenRouterLLMProvider (Chat Completions API)
  → ResponseValidator
  → structured API response
```

Routes and domain services do not import or instantiate the OpenAI SDK. Provider
selection and adapter wiring live in `app/api/dependencies.py`.

## Tests

```powershell
python -m pytest -q
```

Unit tests inject fake LLM clients and make no real OpenAI or OpenRouter request.

## Other configuration

CORS allows `http://localhost:3000` by default. Override it with a JSON array:

```env
CORS_ORIGINS=["http://localhost:3000","http://127.0.0.1:3000"]
```
