"""Conversation use-case orchestration with provider-neutral dependencies."""

from dataclasses import dataclass, field
from uuid import UUID

from app.domain.entities.message import MessageRole
from app.domain.entities.session import CoachingSession
from app.domain.interfaces.conversation_repository import (
    ConversationRepositoryError,
    ConversationSessionRepository,
    MessageRepository,
)
from app.domain.interfaces.llm_provider import (
    LLMIncompleteResponseError,
    LLMProvider,
    LLMProviderError,
)
from app.domain.interfaces.retriever import (
    ChunkRetriever,
    RetrievedChunk,
    RetrievalUnavailableError,
)
from app.domain.services.prompt_builder import PromptBuilder
from app.domain.services.rag_context_policy import RAGContextPolicy
from app.domain.services.response_validator import ResponseValidator
from app.domain.services.safety_service import RiskCategory, SafetyService


@dataclass(frozen=True, slots=True)
class ConversationCommand:
    """Framework-independent input for one user conversation turn."""

    message: str
    user_id: UUID
    session_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class ConversationResult:
    """Structured outcome returned to delivery adapters such as FastAPI."""

    message: str
    status: str
    session_id: UUID | None = None
    memory_items_used: int = 0
    rag_chunks_used: int = 0
    rag_availability: str = "none"
    source_ids: list[str] = field(default_factory=list)
    sources: list["ConversationSource"] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ConversationSource:
    source_id: str
    filename: str
    page_number: int | None
    chunk_index: int | None
    score: float


class ConversationManager:
    """Coordinate a safe coaching response without knowing external providers.

    The manager depends only on domain services and ports. Concrete OpenAI,
    Qdrant, database, voice, or avatar adapters are supplied at the composition
    root and never imported here.
    """

    def __init__(
        self,
        session_repository: ConversationSessionRepository,
        message_repository: MessageRepository,
        retriever: ChunkRetriever,
        prompt_builder: PromptBuilder,
        llm_provider: LLMProvider,
        response_validator: ResponseValidator,
        safety_service: SafetyService,
        rag_context_policy: RAGContextPolicy | None = None,
        *,
        memory_limit: int = 8,
        retrieval_top_k: int = 5,
    ) -> None:
        if memory_limit <= 0:
            raise ValueError("memory_limit must be greater than zero")
        if retrieval_top_k <= 0:
            raise ValueError("retrieval_top_k must be greater than zero")

        self.session_repository = session_repository
        self.message_repository = message_repository
        self.retriever = retriever
        self.prompt_builder = prompt_builder
        self.llm_provider = llm_provider
        self.response_validator = response_validator
        self.safety_service = safety_service
        self.rag_context_policy = rag_context_policy or RAGContextPolicy()
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

        try:
            session = await self._resolve_session(command, user_message)
            stored_user_message = await self.message_repository.add(
                session.id,
                MessageRole.USER,
                user_message,
            )
            recent_messages = await self.message_repository.list_recent(
                session.id,
                self.memory_limit,
                exclude_message_id=stored_user_message.id,
            )
        except ConversationRepositoryError as error:
            raise ConversationPersistenceUnavailableError from error

        memory = [
            f"{message.role.value}: {message.content}" for message in recent_messages
        ]
        try:
            chunks = await self.retriever.retrieve_relevant_chunks(
                user_message,
                top_k=self.retrieval_top_k,
            )
        except RetrievalUnavailableError:
            chunks = []
        context_decision = self.rag_context_policy.select(user_message, chunks)
        chunks = context_decision.chunks
        sources = self._sources(chunks)
        prompt = self.prompt_builder.build(
            user_message=user_message,
            memory_context=memory,
            retrieved_context=[
                {
                    "source_id": chunk.source_id,
                    "filename": chunk.filename,
                    "page_number": chunk.page_number,
                    "chunk_index": chunk.chunk_index,
                    "text": chunk.text,
                }
                for chunk in chunks
            ],
            document_specific=context_decision.document_specific,
            document_context_insufficient=(
                context_decision.insufficient_document_context
            ),
        )
        try:
            generated_response = await self.llm_provider.generate(prompt)
        except LLMIncompleteResponseError as error:
            return ConversationResult(
                message=error.user_message,
                status="llm_incomplete",
                session_id=session.id,
                memory_items_used=len(memory),
                rag_chunks_used=len(chunks),
                rag_availability="provided" if chunks else "none",
            )
        except LLMProviderError as error:
            return ConversationResult(
                message=error.user_message,
                status="llm_unavailable",
                session_id=session.id,
                memory_items_used=len(memory),
                rag_chunks_used=len(chunks),
                rag_availability="provided" if chunks else "none",
            )

        if context_decision.insufficient_document_context:
            generated_response = self.rag_context_policy.add_insufficiency_notice(
                user_message,
                generated_response,
            )

        if not self.response_validator.validate(
            generated_response,
            professional_help_required=(
                safety_assessment.professional_help_recommended
            ),
        ):
            return self._validation_failure(
                session.id,
                memory,
                chunks,
                medical_refusal_required=bool(
                    set(safety_assessment.categories)
                    & {
                        RiskCategory.MEDICAL_DIAGNOSIS_REQUEST,
                        RiskCategory.MEDICATION_REQUEST,
                    }
                ),
            )

        assistant_response = generated_response.strip()
        try:
            await self.message_repository.add(
                session.id,
                MessageRole.ASSISTANT,
                assistant_response,
                metadata={
                    "sources": [
                        {
                            "source_id": source.source_id,
                            "filename": source.filename,
                            "page_number": source.page_number,
                            "chunk_index": source.chunk_index,
                            "score": source.score,
                        }
                        for source in sources
                    ]
                }
                if sources
                else None,
            )
        except ConversationRepositoryError as error:
            raise ConversationPersistenceUnavailableError from error

        return ConversationResult(
            message=assistant_response,
            status="completed",
            session_id=session.id,
            memory_items_used=len(memory),
            rag_chunks_used=len(chunks),
            rag_availability="provided" if chunks else "none",
            source_ids=[source.source_id for source in sources],
            sources=sources,
        )

    @staticmethod
    def _validation_failure(
        session_id: UUID,
        memory: list[str],
        chunks: list[RetrievedChunk],
        *,
        medical_refusal_required: bool = False,
    ) -> ConversationResult:
        """Return a safe failure without leaking a rejected model response."""
        message = (
            "I cannot provide a medical diagnosis or medication prescription. "
            "Please consult a qualified healthcare professional."
            if medical_refusal_required
            else (
                "I could not produce a response that passed the safety and "
                "quality checks. Please try rephrasing your message."
            )
        )
        return ConversationResult(
            message=message,
            status="validation_failed",
            session_id=session_id,
            memory_items_used=len(memory),
            rag_chunks_used=len(chunks),
            rag_availability="provided" if chunks else "none",
        )

    @staticmethod
    def _sources(chunks: list[RetrievedChunk]) -> list[ConversationSource]:
        return [
            ConversationSource(
                source_id=chunk.source_id,
                filename=chunk.filename,
                page_number=chunk.page_number,
                chunk_index=chunk.chunk_index,
                score=chunk.score,
            )
            for chunk in chunks
        ]

    async def _resolve_session(
        self, command: ConversationCommand, message: str
    ) -> CoachingSession:
        """Create a session or enforce ownership of the supplied session."""
        if command.session_id is None:
            title = message[:157] + "..." if len(message) > 160 else message
            return await self.session_repository.create(command.user_id, title)

        session = await self.session_repository.get_owned(
            command.session_id, command.user_id
        )
        if session is None:
            raise ConversationSessionAccessError
        return session


class ConversationSessionAccessError(LookupError):
    """The requested session does not exist or belongs to another user."""


class ConversationPersistenceUnavailableError(RuntimeError):
    """Conversation persistence is temporarily unavailable."""
