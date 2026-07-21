"""FastAPI application factory and composition root."""

import logging
from contextlib import asynccontextmanager

from asyncpg import PostgresError
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes import (
    auth_routes,
    conversation_routes,
    document_routes,
    health_routes,
    voice_routes,
)
from app.core.config import settings
from app.core.logging import configure_logging
from app.infrastructure.database.postgres import (
    close_database_engine,
    initialize_database,
)


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Initialize development tables without making database failure fatal."""
    if settings.database_auto_create:
        try:
            await initialize_database()
        except (SQLAlchemyError, PostgresError, OSError) as error:
            # Driver-level connection failures (including asyncpg authentication
            # errors) are not always wrapped in SQLAlchemyError. Database access
            # is optional for liveness, so start the API and keep auth endpoints
            # safely unavailable until configuration is corrected.
            logger.warning(
                "Database initialization failed: error_type=%s cause_type=%s",
                type(error).__name__,
                _root_error_type(error),
            )
    yield
    await close_database_engine()


def _root_error_type(error: BaseException) -> str:
    """Return only the deepest exception type, never its sensitive message."""
    current = error
    seen: set[int] = set()
    while id(current) not in seen:
        seen.add(id(current))
        nested = current.__cause__ or current.__context__
        if nested is None:
            break
        current = nested
    return type(current).__name__


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
        conversation_routes.router,
        document_routes.router,
        voice_routes.router,
    )
    for router in routers:
        application.include_router(router, prefix=settings.api_prefix)

    return application


app = create_app()
