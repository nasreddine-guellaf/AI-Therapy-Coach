"""Conversation use-case orchestration with provider-neutral dependencies."""

from dataclasses import dataclass, field
from uuid import UUID

from app.domain.interfaces.llm_provider import LLMProvider, LLMProviderError
from app.domain.interfaces.retriever import ChunkRetriever, RetrievedChunk
from app.domain.services.memory_service import MemoryService
from app.domain.services.prompt_builder import PromptBuilder
from app.domain.services.response_validator import ResponseValidator
from app.domain.services.safety_service import SafetyService


@dataclass(frozen=True, slots=True)
class ConversationCommand:
    """Framework-independent input for one user conversation turn."""

    message: str
    user_id: UUID
    session_id: str | None = None


@dataclass(frozen=True, slots=True)
class ConversationResult:
    """Structured outcome returned to delivery adapters such as FastAPI."""

    message: str
    status: str
    memory_items_used: int = 0
    rag_chunks_used: int = 0
    source_ids: list[str] = field(default_factory=list)


class ConversationManager:
    """Coordinate a safe coaching response without knowing external providers.

    The manager depends only on domain services and ports. Concrete OpenAI,
    Qdrant, database, voice, or avatar adapters are supplied at the composition
    root and never imported here.
    """

    def __init__(
        self,
        memory_service: MemoryService,
        retriever: ChunkRetriever,
        prompt_builder: PromptBuilder,
        llm_provider: LLMProvider,
        response_validator: ResponseValidator,
        safety_service: SafetyService,
        *,
        memory_limit: int = 10,
        retrieval_top_k: int = 5,
    ) -> None:
        if memory_limit <= 0:
            raise ValueError("memory_limit must be greater than zero")
        if retrieval_top_k <= 0:
            raise ValueError("retrieval_top_k must be greater than zero")

        self.memory_service = memory_service
        self.retriever = retriever
        self.prompt_builder = prompt_builder
        self.llm_provider = llm_provider
        self.response_validator = response_validator
        self.safety_service = safety_service
        self.memory_limit = memory_limit
        self.retrieval_top_k = retrieval_top_k

    async def handle(self, command: ConversationCommand) -> ConversationResult:
        """Execute one conversation turn through safety, context, and generation.

        Critical messages are escalated before memory retrieval or LLM use. For
        ordinary messages, recent memory and RAG evidence are loaded, passed to
        the prompt builder, generated through ``LLMProvider``, and validated
        before a structured result is returned.
        """
        user_message = command.message.strip()
        if not user_message:
            raise ValueError("message cannot be empty")

        safety_assessment = self.safety_service.assess(user_message)
        if safety_assessment.requires_immediate_escalation:
            return ConversationResult(
                message=self.safety_service.crisis_message(),
                status="escalation_required",
            )

        memory = await self.memory_service.recent_context(
            command.session_id, limit=self.memory_limit
        )
        chunks = await self.retriever.retrieve_relevant_chunks(
            user_message, top_k=self.retrieval_top_k
        )
        prompt = self.prompt_builder.build(
            user_message=user_message,
            memory_context=memory,
            retrieved_context=[chunk.text for chunk in chunks],
        )
        try:
            generated_response = await self.llm_provider.generate(prompt)
        except LLMProviderError as error:
            return ConversationResult(
                message=error.user_message,
                status="llm_unavailable",
                memory_items_used=len(memory),
                rag_chunks_used=len(chunks),
                source_ids=[chunk.id for chunk in chunks],
            )

        if not self.response_validator.validate(
            generated_response,
            professional_help_required=(
                safety_assessment.professional_help_recommended
            ),
        ):
            return self._validation_failure(memory, chunks)

        return ConversationResult(
            message=generated_response.strip(),
            status="completed",
            memory_items_used=len(memory),
            rag_chunks_used=len(chunks),
            source_ids=[chunk.id for chunk in chunks],
        )

    @staticmethod
    def _validation_failure(
        memory: list[str], chunks: list[RetrievedChunk]
    ) -> ConversationResult:
        """Return a safe failure without leaking a rejected model response."""
        return ConversationResult(
            message=(
                "I could not produce a response that passed the safety and "
                "quality checks. Please try rephrasing your message."
            ),
            status="validation_failed",
            memory_items_used=len(memory),
            rag_chunks_used=len(chunks),
            source_ids=[chunk.id for chunk in chunks],
        )
