"""FastAPI composition providers for application use cases."""

from functools import lru_cache

from app.domain.interfaces.llm_provider import LLMProvider
from app.domain.interfaces.retriever import ChunkRetriever, RetrievedChunk
from app.domain.services.conversation_manager import ConversationManager
from app.domain.services.memory_service import MemoryService
from app.domain.services.prompt_builder import PromptBuilder
from app.domain.services.response_validator import ResponseValidator
from app.domain.services.safety_service import SafetyService


class _EmptyRetriever(ChunkRetriever):
    """No-network adapter used until vector retrieval is configured."""

    async def retrieve_relevant_chunks(
        self, query: str, top_k: int = 5
    ) -> list[RetrievedChunk]:
        return []


class _PlaceholderLLMProvider(LLMProvider):
    """Safe local provider that makes the API runnable without OpenAI."""

    async def generate(self, prompt: str) -> str:
        return (
            "The language model provider is not configured yet. "
            "No external AI service was called."
        )


@lru_cache
def get_conversation_manager() -> ConversationManager:
    """Compose the conversation use case with no-network initial adapters."""
    # TODO: replace these placeholders with configured repository, retriever,
    # and LLM adapters at startup without changing the domain manager.
    return ConversationManager(
        memory_service=MemoryService(),
        retriever=_EmptyRetriever(),
        prompt_builder=PromptBuilder(),
        llm_provider=_PlaceholderLLMProvider(),
        response_validator=ResponseValidator(),
        safety_service=SafetyService(),
    )
