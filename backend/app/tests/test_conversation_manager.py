"""Expected orchestration behavior for the conversation use case."""

import asyncio

from app.domain.interfaces.llm_provider import LLMProvider
from app.domain.interfaces.retriever import ChunkRetriever, RetrievedChunk
from app.domain.services.conversation_manager import (
    ConversationCommand,
    ConversationManager,
)
from app.domain.services.memory_service import MemoryService
from app.domain.services.prompt_builder import PromptBuilder
from app.domain.services.response_validator import ResponseValidator
from app.domain.services.safety_service import SafetyService


class StubMemoryService(MemoryService):
    def __init__(self, events: list[str]) -> None:
        self.events = events

    async def recent_context(
        self, session_id: str | None, limit: int = 10
    ) -> list[str]:
        self.events.append("memory")
        assert session_id == "session-1"
        return ["The user prefers short exercises."]


class StubRetriever(ChunkRetriever):
    def __init__(self, events: list[str]) -> None:
        self.events = events

    async def retrieve_relevant_chunks(
        self, query: str, top_k: int = 5
    ) -> list[RetrievedChunk]:
        self.events.append("retrieval")
        return [
            RetrievedChunk(
                id="chunk-1",
                text="A short breathing pause can support reflection.",
                score=0.92,
                metadata={"page_number": 4},
            )
        ]


class StubLLMProvider(LLMProvider):
    def __init__(self, events: list[str], response: str = "Would a short pause help?") -> None:
        self.events = events
        self.response = response
        self.prompt = ""

    async def generate(self, prompt: str) -> str:
        self.events.append("llm")
        self.prompt = prompt
        return self.response


class TrackingValidator(ResponseValidator):
    def __init__(self, events: list[str]) -> None:
        self.events = events

    def validate(self, response: str) -> bool:
        self.events.append("validation")
        return super().validate(response)


def build_manager(
    events: list[str], *, llm_response: str = "Would a short pause help?"
) -> tuple[ConversationManager, StubLLMProvider]:
    llm = StubLLMProvider(events, llm_response)
    manager = ConversationManager(
        memory_service=StubMemoryService(events),
        retriever=StubRetriever(events),
        prompt_builder=PromptBuilder(),
        llm_provider=llm,
        response_validator=TrackingValidator(events),
        safety_service=SafetyService(),
    )
    return manager, llm


def test_manager_orchestrates_context_generation_and_validation() -> None:
    """Memory and RAG context should reach the LLM before validation."""
    events: list[str] = []
    manager, llm = build_manager(events)

    result = asyncio.run(
        manager.handle(
            ConversationCommand(message="I feel tense", session_id="session-1")
        )
    )

    assert events == ["memory", "retrieval", "llm", "validation"]
    assert "short exercises" in llm.prompt
    assert "breathing pause" in llm.prompt
    assert result.status == "completed"
    assert result.memory_items_used == 1
    assert result.rag_chunks_used == 1
    assert result.source_ids == ["chunk-1"]


def test_manager_rejects_an_invalid_llm_response() -> None:
    """A rejected response must not be returned to the user."""
    events: list[str] = []
    manager, _ = build_manager(events, llm_response="   ")

    result = asyncio.run(
        manager.handle(
            ConversationCommand(message="I feel tense", session_id="session-1")
        )
    )

    assert result.status == "validation_failed"
    assert result.message.strip()


def test_crisis_message_short_circuits_memory_retrieval_and_llm() -> None:
    """Explicit crisis input must return fixed guidance without external calls."""
    events: list[str] = []
    manager, _ = build_manager(events)

    result = asyncio.run(
        manager.handle(
            ConversationCommand(
                message="Je pense au suicide", session_id="session-1"
            )
        )
    )

    assert result.status == "escalation_required"
    assert events == []
