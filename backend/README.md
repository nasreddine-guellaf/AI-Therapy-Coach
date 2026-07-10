# AI Therapy Coach Backend

Minimal FastAPI backend for the AI Therapy Coach project. The application exposes
the initial HTTP routes while OpenAI, Qdrant, Whisper, and ElevenLabs remain
interfaces or unimplemented adapters.

## Requirements

- Python 3.12+
- `pip`

## Run locally

From the `backend` directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

On macOS or Linux, activate the environment with:

```bash
source .venv/bin/activate
```

Then open:

- Health endpoint: <http://127.0.0.1:8000/api/health>
- Swagger UI: <http://127.0.0.1:8000/docs>
- ReDoc: <http://127.0.0.1:8000/redoc>

## Configuration

Settings are read from environment variables or the repository-level `.env`
file. CORS allows `http://localhost:3000` by default. To override it, provide a
JSON array through `CORS_ORIGINS`, for example:

```env
CORS_ORIGINS=["http://localhost:3000","http://127.0.0.1:3000"]
```

## Tests

```powershell
python -m pytest -q
```

The health route is runnable without PostgreSQL, Qdrant, OpenAI, Whisper, or
ElevenLabs.
