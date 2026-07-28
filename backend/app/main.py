"""FastAPI application factory and composition root."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    auth_routes,
    conversation_history_routes,
    conversation_routes,
    document_routes,
    health_routes,
    voice_routes,
)
from app.core.config import settings
from app.core.logging import configure_logging
from app.infrastructure.database.postgres import close_database_engine


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Dispose database resources; schema changes are owned by Alembic."""
    yield
    await close_database_engine()


def create_app() -> FastAPI:
    """Create and configure the HTTP application without starting integrations."""
    configure_logging()

    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Minimal API for the AI Therapy Coach project.",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    routers = (
        health_routes.router,
        auth_routes.router,
        conversation_history_routes.router,
        conversation_routes.router,
        document_routes.router,
        voice_routes.router,
    )
    for router in routers:
        application.include_router(router, prefix=settings.api_prefix)

    return application


app = create_app()
