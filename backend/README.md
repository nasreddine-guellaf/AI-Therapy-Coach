# Backend

API FastAPI structurée en couches : `domain` contient le métier et ses ports, `infrastructure` les adaptateurs, `api` les transports HTTP, `schemas` les DTO et `core` la configuration transversale.

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
pytest
```
