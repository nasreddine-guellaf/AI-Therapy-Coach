"""Conversation persistence and orchestration behavior."""

import asyncio
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import pytest

from app.domain.entities.message import Message, MessageRole
from app.domain.entities.session import CoachingSession
from app.domain.entities.session import ConversationSummary
from app.domain.interfaces.conversation_repository import (
    ConversationSessionRepository,
    MessageRepository,
)
from app.domain.interfaces.llm_provider import (
    LLMIncompleteResponseError,
    LLMNotConfiguredError,
    LLMPrompt,
    LLMProvider,
)
from app.domain.interfaces.retriever import ChunkRetriever, RetrievedChunk
from app.domain.services.conversation_manager import (
    ConversationCommand,
    ConversationManager,
    ConversationSessionAccessError,
)
from app.domain.services.prompt_builder import PromptBuilder
from app.domain.services.response_validator import ResponseValidator
from app.domain.services.safety_service import SafetyService


USER_ID = UUID("00000000-0000-0000-0000-000000000001")
OTHER_USER_ID = UUID("00000000-0000-0000-0000-000000000002")
SESSION_ID = UUID("10000000-0000-0000-0000-000000000001")
NOW = datetime.now(timezone.utc)


class FakeSessionRepository(ConversationSessionRepository):
    def __init__(self) -> None:
        self.sessions: dict[UUID, CoachingSession] = {
            SESSION_ID: CoachingSession(
                id=SESSION_ID,
                user_id=USER_ID,
                title="Existing",
                created_at=NOW,
                updated_at=NOW,
            )
        }
        self.created: list[CoachingSession] = []

    async def create(self, user_id: UUID, title: str | None) -> CoachingSession:
        session = CoachingSession(user_id=user_id, title=title)
        self.sessions[session.id] = session
        self.created.append(session)
        return session

    async def get_owned(
        self, session_id: UUID, user_id: UUID
    ) -> CoachingSession | None:
        session = self.sessions.get(session_id)
        return session if session and session.user_id == user_id else None

    async def list_for_user(
        self, user_id: UUID, limit: int = 50
    ) -> list[ConversationSummary]:
        return []

    async def delete_owned(self, session_id: UUID, user_id: UUID) -> bool:
        session = await self.get_owned(session_id, user_id)
        if session is None:
            return False
        del self.sessions[session_id]
        return True


class FakeMessageRepository(MessageRepository):
    def __init__(self, history: list[Message] | None = None) -> None:
        self.messages = list(history or [])
        self.history_limit: int | None = None
        self.excluded_message_id: UUID | None = None

    async def add(
        self,
        session_id: UUID,
        role: MessageRole,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> Message:
        message = Message(
            id=uuid4(),
            session_id=session_id,
            role=role,
            content=content,
            metadata=metadata,
        )
        self.messages.append(message)
        return message

    async def list_recent(
        self,
        session_id: UUID,
        limit: int,
        *,
        exclude_message_id: UUID | None = None,
    ) -> list[Message]:
        self.history_limit = limit
        self.excluded_message_id = exclude_message_id
        matches = [
            item
            for item in self.messages
            if item.session_id == session_id and item.id != exclude_message_id
        ]
        return matches[-limit:]

    async def list_for_session(self, session_id: UUID) -> list[Message]:
        return [item for item in self.messages if item.session_id == session_id]


class EmptyRetriever(ChunkRetriever):
    async def retrieve_relevant_chunks(
        self, query: str, top_k: int = 5
    ) -> list[RetrievedChunk]:
        return []


class StubLLMProvider(LLMProvider):
    def __init__(self, response: str = "Would a short pause help?") -> None:
        self.response = response
        self.prompt: LLMPrompt | None = None

    async def generate(self, prompt: LLMPrompt) -> str:
        self.prompt = prompt
        return self.response


def build_manager(
    *,
    sessions: FakeSessionRepository | None = None,
    messages: FakeMessageRepository | None = None,
    llm: LLMProvider | None = None,
    retriever: ChunkRetriever | None = None,
) -> tuple[ConversationManager, FakeSessionRepository, FakeMessageRepository, LLMProvider]:
    session_repository = sessions or FakeSessionRepository()
    message_repository = messages or FakeMessageRepository()
    provider = llm or StubLLMProvider()
    return (
        ConversationManager(
            session_repository=session_repository,
            message_repository=message_repository,
            retriever=retriever or EmptyRetriever(),
            prompt_builder=PromptBuilder(),
            llm_provider=provider,
            response_validator=ResponseValidator(),
            safety_service=SafetyService(),
            memory_limit=8,
        ),
        session_repository,
        message_repository,
        provider,
    )


def test_new_session_and_both_messages_are_stored() -> None:
    manager, sessions, messages, _ = build_manager()

    result = asyncio.run(
        manager.handle(ConversationCommand(message="I feel tense", user_id=USER_ID))
    )

    assert len(sessions.created) == 1
    assert result.session_id == sessions.created[0].id
    assert [item.role for item in messages.messages] == [
        MessageRole.USER,
        MessageRole.ASSISTANT,
    ]
    assert result.status == "completed"


def test_existing_session_must_belong_to_authenticated_user() -> None:
    manager, _, messages, _ = build_manager()

    with pytest.raises(ConversationSessionAccessError):
        asyncio.run(
            manager.handle(
                ConversationCommand(
                    message="Private message",
                    user_id=OTHER_USER_ID,
                    session_id=SESSION_ID,
                )
            )
        )

    assert messages.messages == []


def test_recent_history_is_loaded_into_prompt_without_duplicating_current_turn() -> None:
    history = [
        Message(SESSION_ID, MessageRole.USER, "Earlier concern"),
        Message(SESSION_ID, MessageRole.ASSISTANT, "Earlier reflection"),
    ]
    message_repository = FakeMessageRepository(history)
    provider = StubLLMProvider()
    manager, _, messages, _ = build_manager(messages=message_repository, llm=provider)

    result = asyncio.run(
        manager.handle(
            ConversationCommand(
                message="Current concern", user_id=USER_ID, session_id=SESSION_ID
            )
        )
    )

    assert provider.prompt is not None
    assert "user: Earlier concern" in provider.prompt.input
    assert "assistant: Earlier reflection" in provider.prompt.input
    assert provider.prompt.input.count("Current concern") == 1
    assert messages.history_limit == 8
    assert messages.excluded_message_id is not None
    assert result.memory_items_used == 2


def test_invalid_response_is_not_stored_as_assistant_message() -> None:
    manager, _, messages, _ = build_manager(llm=StubLLMProvider("   "))
    result = asyncio.run(
        manager.handle(
            ConversationCommand(message="I feel tense", user_id=USER_ID)
        )
    )
    assert result.status == "validation_failed"
    assert [item.role for item in messages.messages] == [MessageRole.USER]


def test_crisis_message_short_circuits_persistence_and_llm() -> None:
    manager, sessions, messages, _ = build_manager()
    result = asyncio.run(
        manager.handle(
            ConversationCommand(message="Je pense au suicide", user_id=USER_ID)
        )
    )
    assert result.status == "escalation_required"
    assert sessions.created == []
    assert messages.messages == []


def test_llm_unavailable_keeps_stored_user_turn_and_returns_session() -> None:
    class MissingProvider(LLMProvider):
        async def generate(self, prompt: LLMPrompt) -> str:
            raise LLMNotConfiguredError

    manager, _, messages, _ = build_manager(llm=MissingProvider())
    result = asyncio.run(
        manager.handle(ConversationCommand(message="I feel tense", user_id=USER_ID))
    )
    assert result.status == "llm_unavailable"
    assert result.session_id is not None
    assert [item.role for item in messages.messages] == [MessageRole.USER]
    assert result.source_ids == []
    assert result.sources == []


def test_incomplete_llm_response_is_not_stored_or_attributed() -> None:
    class IncompleteProvider(LLMProvider):
        async def generate(self, prompt: LLMPrompt) -> str:
            raise LLMIncompleteResponseError

    class GroundedRetriever(ChunkRetriever):
        async def retrieve_relevant_chunks(
            self, query: str, top_k: int = 5
        ) -> list[RetrievedChunk]:
            return [
                RetrievedChunk(
                    id="point-1",
                    text="Grounding that must not be attributed to a failure.",
                    score=0.91,
                    metadata={
                        "source_id": "source-1",
                        "filename": "guide.pdf",
                        "page_number": 3,
                    },
                )
            ]

    manager, _, messages, _ = build_manager(
        llm=IncompleteProvider(),
        retriever=GroundedRetriever(),
    )
    result = asyncio.run(
        manager.handle(ConversationCommand(message="I feel tense", user_id=USER_ID))
    )

    assert result.status == "llm_incomplete"
    assert result.rag_chunks_used == 1
    assert [item.role for item in messages.messages] == [MessageRole.USER]
    assert result.source_ids == []
    assert result.sources == []


def test_unanswerable_retrieval_returns_no_sources_and_marks_context_none() -> None:
    provider = StubLLMProvider(
        "The documents do not provide enough information about that."
    )
    manager, _, _, _ = build_manager(llm=provider, retriever=EmptyRetriever())
    result = asyncio.run(
        manager.handle(
            ConversationCommand(
                message="What is tomorrow's weather?",
                user_id=USER_ID,
            )
        )
    )

    assert provider.prompt is not None
    assert "availability=none" in provider.prompt.input
    assert result.status == "completed"
    assert result.rag_availability == "none"
    assert result.rag_chunks_used == 0
    assert result.source_ids == []
    assert result.sources == []


def test_general_coaching_without_chunks_still_calls_llm_without_sources() -> None:
    provider = StubLLMProvider(
        "It may help to pause, name the feeling, and choose one small next step."
    )
    manager, _, messages, _ = build_manager(
        llm=provider,
        retriever=EmptyRetriever(),
    )

    result = asyncio.run(
        manager.handle(
            ConversationCommand(
                message="I feel overwhelmed. Can you help me reflect?",
                user_id=USER_ID,
            )
        )
    )

    assert provider.prompt is not None
    assert "question_scope=general_coaching" in provider.prompt.input
    assert result.status == "completed"
    assert result.rag_chunks_used == 0
    assert result.rag_availability == "none"
    assert result.source_ids == []
    assert result.sources == []
    assert messages.messages[-1].role is MessageRole.ASSISTANT
    assert messages.messages[-1].metadata is None


def test_weak_document_question_adds_insufficiency_notice_and_fallback() -> None:
    class WeakRetriever(ChunkRetriever):
        async def retrieve_relevant_chunks(
            self, query: str, top_k: int = 5
        ) -> list[RetrievedChunk]:
            return [
                RetrievedChunk(
                    id="weak-point",
                    text="A weakly related passage.",
                    score=0.30,
                    metadata={
                        "source_id": "weak-source",
                        "filename": "guide.pdf",
                    },
                )
            ]

    provider = StubLLMProvider(
        "Tu peux commencer par identifier une petite étape concrète."
    )
    manager, _, _, _ = build_manager(
        llm=provider,
        retriever=WeakRetriever(),
    )

    result = asyncio.run(
        manager.handle(
            ConversationCommand(
                message="Selon les documents, que faire dans cette situation ?",
                user_id=USER_ID,
            )
        )
    )

    assert provider.prompt is not None
    assert "availability=none" in provider.prompt.input
    assert "document_context_insufficient=true" in provider.prompt.input
    assert result.status == "completed"
    assert result.message.startswith(
        "Les documents disponibles ne donnent pas assez "
        "d\u2019informations sur ce point."
    )
    assert "petite étape" in result.message
    assert result.rag_chunks_used == 0
    assert result.rag_availability == "none"
    assert result.source_ids == []
    assert result.sources == []


def test_medical_prescription_request_returns_safe_refusal() -> None:
    provider = StubLLMProvider("Take 20 mg of this medication every day.")
    manager, _, messages, _ = build_manager(
        llm=provider,
        retriever=EmptyRetriever(),
    )

    result = asyncio.run(
        manager.handle(
            ConversationCommand(
                message="What dosage of antidepressant should I take?",
                user_id=USER_ID,
            )
        )
    )

    assert provider.prompt is not None
    assert result.status == "validation_failed"
    assert "cannot provide" in result.message
    assert "qualified healthcare professional" in result.message
    assert result.sources == []
    assert [message.role for message in messages.messages] == [MessageRole.USER]


def test_empty_rag_context_never_returns_fake_structured_sources() -> None:
    provider = StubLLMProvider("A general coaching reflection can still help.")
    manager, _, _, _ = build_manager(
        llm=provider,
        retriever=EmptyRetriever(),
    )

    result = asyncio.run(
        manager.handle(
            ConversationCommand(message="Help me reflect", user_id=USER_ID)
        )
    )

    assert provider.prompt is not None
    assert "Never create fake citations" in provider.prompt.instructions
    assert "availability=none" in provider.prompt.input
    assert result.status == "completed"
    assert result.source_ids == []
    assert result.sources == []


def test_rag_context_and_sources_are_returned_and_persisted() -> None:
    class GroundedRetriever(ChunkRetriever):
        async def retrieve_relevant_chunks(
            self, query: str, top_k: int = 5
        ) -> list[RetrievedChunk]:
            return [
                RetrievedChunk(
                    id="point-1",
                    text="The guide recommends one small achievable step.",
                    score=0.91,
                    metadata={
                        "source_id": "source-1",
                        "filename": "guide.pdf",
                        "page_number": 3,
                        "chunk_index": 2,
                    },
                )
            ]

    provider = StubLLMProvider()
    manager, _, messages, _ = build_manager(
        llm=provider, retriever=GroundedRetriever()
    )
    result = asyncio.run(
        manager.handle(ConversationCommand(message="What does my guide say?", user_id=USER_ID))
    )

    assert provider.prompt is not None
    assert "The guide recommends one small achievable step." in provider.prompt.input
    assert result.source_ids == ["source-1"]
    assert result.sources[0].filename == "guide.pdf"
    assert result.rag_chunks_used == 1
    assert result.rag_availability == "provided"
    assert messages.messages[-1].metadata == {
        "sources": [
            {
                "source_id": "source-1",
                "filename": "guide.pdf",
                "page_number": 3,
                "chunk_index": 2,
                "score": 0.91,
            }
        ]
    }
