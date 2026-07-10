"""FastAPI composition root; dependency wiring belongs here."""
from fastapi import FastAPI
from app.api.routes import conversation_routes, document_routes, health_routes, voice_routes
from app.core.config import settings
from app.core.logging import configure_logging

configure_logging()
app = FastAPI(title=settings.app_name, version="0.1.0")
for router in (conversation_routes.router, document_routes.router, voice_routes.router, health_routes.router):
    app.include_router(router, prefix="/api")
