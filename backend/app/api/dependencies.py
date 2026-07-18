"""FastAPI composition providers for application use cases."""

import logging
from functools import lru_cache

from app.core.config import settings
from app.domain.interfaces.llm_provider import LLMProvider
from app.domain.interfaces.retriever import ChunkRetriever, RetrievedChunk
from app.domain.services.conversation_manager import ConversationManager
from app.domain.services.memory_service import MemoryService
from app.domain.services.prompt_builder import PromptBuilder
from app.domain.services.response_validator import ResponseValidator
from app.domain.services.safety_service import SafetyService
from app.infrastructure.llm.openai_client import OpenAILLMProvider
from app.infrastructure.llm.openrouter_client import OpenRouterLLMProvider


logger = logging.getLogger(__name__)


class _EmptyRetriever(ChunkRetriever):
    """No-network adapter used until vector retrieval is configured."""

    async def retrieve_relevant_chunks(
        self, query: str, top_k: int = 5
    ) -> list[RetrievedChunk]:
        return []


def build_llm_provider() -> LLMProvider:
    """Create the configured provider adapter at the application boundary."""
    if settings.llm_provider == "openrouter":
        logger.info(
            "LLM configuration: provider=%s api_key_present=%s model=%s",
            settings.llm_provider,
            bool(
                settings.openrouter_api_key
                and settings.openrouter_api_key.strip()
            ),
            settings.openrouter_model,
        )
        return OpenRouterLLMProvider(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            model=settings.openrouter_model,
            timeout_seconds=settings.openai_timeout_seconds,
            max_output_tokens=settings.openai_max_output_tokens,
        )

    logger.info(
        "LLM configuration: provider=%s api_key_present=%s model=%s",
        settings.llm_provider,
        bool(settings.openai_api_key and settings.openai_api_key.strip()),
        settings.openai_model,
    )
    return OpenAILLMProvider(
        api_key=settings.openai_api_key,
        model=settings.openai_model,
        timeout_seconds=settings.openai_timeout_seconds,
        max_output_tokens=settings.openai_max_output_tokens,
    )


@lru_cache
def get_conversation_manager() -> ConversationManager:
    """Compose the use case with the selected provider adapter."""
    return ConversationManager(
        memory_service=MemoryService(),
        retriever=_EmptyRetriever(),
        prompt_builder=PromptBuilder(),
        llm_provider=build_llm_provider(),
        response_validator=ResponseValidator(),
        safety_service=SafetyService(),
    )
