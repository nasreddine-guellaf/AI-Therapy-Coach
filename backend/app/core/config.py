from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Environment-backed settings; secrets must never be committed."""
    app_name: str = "Therapeutic AI Coach API"
    app_env: str = "development"
    database_url: str = "postgresql+asyncpg://therapeutic:therapeutic@localhost:5432/therapeutic_ai"
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    openai_api_key: str | None = None
    elevenlabs_api_key: str | None = None
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
