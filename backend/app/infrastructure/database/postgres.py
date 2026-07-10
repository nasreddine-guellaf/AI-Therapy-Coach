from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from app.core.config import settings

def create_engine() -> AsyncEngine:
    """Create the engine only; migrations and sessions are future work."""
    return create_async_engine(settings.database_url, pool_pre_ping=True)
