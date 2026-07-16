"""Asynchronous PostgreSQL connection and session configuration."""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings


def create_database_engine(database_url: str | None = None) -> AsyncEngine:
    """Build a pooled async engine without opening a connection immediately."""
    return create_async_engine(
        database_url or settings.database_url,
        pool_pre_ping=True,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        echo=settings.database_echo,
    )


engine = create_database_engine()
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_database_session() -> AsyncIterator[AsyncSession]:
    """Yield one transaction-scoped session for future FastAPI dependencies."""
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def close_database_engine() -> None:
    """Dispose pooled connections during application shutdown."""
    await engine.dispose()
