from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed settings; secrets must never be committed."""

    app_name: str = "Therapeutic AI Coach API"
    app_env: str = "development"
    api_prefix: str = "/api"
    cors_origins: list[str] = ["http://localhost:3000"]
    database_url: str = "postgresql+asyncpg://therapeutic:therapeutic@localhost:5432/therapeutic_ai"
    database_pool_size: int = 5
    database_max_overflow: int = 10
    database_echo: bool = False
    database_connect_timeout_seconds: float = Field(default=5.0, gt=0, le=60)
    database_auto_create: bool = True
    secret_key: str | None = None
    access_token_expire_minutes: int = Field(default=30, gt=0, le=10_080)
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    llm_provider: Literal["openai", "openrouter"] = "openai"
    openai_api_key: str | None = None
    openai_model: str = "gpt-5.6-luna"
    openai_timeout_seconds: float = 30.0
    openai_max_output_tokens: int = 700
    openrouter_api_key: str | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "qwen/qwen3-next-80b-a3b-instruct:free"
    elevenlabs_api_key: str | None = None
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
