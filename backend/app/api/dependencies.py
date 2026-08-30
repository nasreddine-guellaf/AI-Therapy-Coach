"""FastAPI composition providers for application use cases."""

import logging
from functools import lru_cache

from app.core.config import settings
from app.domain.interfaces.llm_provider import LLMProvider
from app.domain.interfaces.embedding_provider import EmbeddingProvider
from app.domain.interfaces.retriever import ChunkRetriever
from app.domain.services.conversation_manager import ConversationManager
from app.domain.services.conversation_history_service import ConversationHistoryService
from app.domain.services.prompt_builder import PromptBuilder
from app.domain.services.response_validator import ResponseValidator
from app.domain.services.rag_readiness_service import RAGReadinessService
from app.domain.services.rag_context_policy import RAGContextPolicy
from app.domain.services.safety_service import SafetyService
from app.infrastructure.llm.gemini_client import GeminiLLMProvider
from app.infrastructure.llm.openai_client import OpenAILLMProvider
from app.infrastructure.llm.openrouter_client import OpenRouterLLMProvider
from app.infrastructure.database.conversation_repositories import (
    PostgreSQLConversationSessionRepository,
    PostgreSQLMessageRepository,
)
from app.infrastructure.rag.embeddings import LocalE5EmbeddingProvider
from app.infrastructure.rag.retriever import Retriever
from app.infrastructure.vector_db.qdrant_client import QdrantVectorStore


logger = logging.getLogger(__name__)


def build_llm_provider() -> LLMProvider:
    """Create the configured provider adapter at the application boundary."""
    if settings.llm_provider == "gemini":
        logger.info(
            "LLM configuration: provider=%s api_key_present=%s model=%s",
            settings.llm_provider,
            bool(settings.gemini_api_key and settings.gemini_api_key.strip()),
            settings.gemini_model,
        )
        return GeminiLLMProvider(
            api_key=settings.gemini_api_key,
            base_url=settings.gemini_base_url,
            model=settings.gemini_model,
            timeout_seconds=settings.openai_timeout_seconds,
            max_output_tokens=settings.gemini_max_output_tokens,
        )

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
        session_repository=PostgreSQLConversationSessionRepository(),
        message_repository=PostgreSQLMessageRepository(),
        retriever=get_chunk_retriever(),
        prompt_builder=PromptBuilder(),
        llm_provider=build_llm_provider(),
        response_validator=ResponseValidator(),
        safety_service=SafetyService(),
        rag_context_policy=RAGContextPolicy(
            settings.rag_document_question_min_score
        ),
        retrieval_top_k=settings.rag_top_k,
    )


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    return LocalE5EmbeddingProvider(settings.embedding_model)


@lru_cache
def get_vector_store() -> QdrantVectorStore:
    return QdrantVectorStore()


@lru_cache
def get_chunk_retriever() -> ChunkRetriever:
    return Retriever(
        get_embedding_provider(),
        get_vector_store(),
        min_score=settings.rag_min_score,
    )


@lru_cache
def get_rag_readiness_service() -> RAGReadinessService:
    return RAGReadinessService(
        get_vector_store(),
        expected_pdf_count=3,
        embedding_model=settings.embedding_model,
    )


@lru_cache
def get_conversation_history_service() -> ConversationHistoryService:
    """Compose authenticated history use cases with PostgreSQL adapters."""
    return ConversationHistoryService(
        session_repository=PostgreSQLConversationSessionRepository(),
        message_repository=PostgreSQLMessageRepository(),
    )
