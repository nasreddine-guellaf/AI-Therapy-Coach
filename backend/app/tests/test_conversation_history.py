"""Authenticated conversation history behavior and HTTP contracts."""

import asyncio
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api.auth_dependencies import get_current_user
from app.api.dependencies import get_conversation_history_service
from app.domain.entities.message import Message, MessageRole
from app.domain.entities.session import CoachingSession, ConversationSummary
from app.domain.entities.user import User
from app.domain.interfaces.conversation_repository import (
    ConversationSessionRepository,
    MessageRepository,
)
from app.domain.services.conversation_history_service import (
    ConversationHistoryNotFoundError,
    ConversationHistoryService,
)
from app.main import app


USER_ID = UUID("00000000-0000-0000-0000-000000000001")
OTHER_USER_ID = UUID("00000000-0000-0000-0000-000000000002")
SESSION_ID = UUID("10000000-0000-0000-0000-000000000001")
NOW = datetime.now(timezone.utc)
SESSION = CoachingSession(
    id=SESSION_ID,
    user_id=USER_ID,
    title="Managing workload",
    created_at=NOW,
    updated_at=NOW,
)
USER = User(
    id=USER_ID,
    email="person@example.com",
    hashed_password="not-serialized",
    full_name="Test Person",
    is_active=True,
    created_at=NOW,
    updated_at=NOW,
)


class HistorySessionRepository(ConversationSessionRepository):
    def __init__(self) -> None:
        self.sessions = {SESSION_ID: SESSION}
        self.listed_user_id: UUID | None = None
        self.deleted: list[UUID] = []

    async def create(self, user_id: UUID, title: str | None) -> CoachingSession:
        raise AssertionError("Not used by history")

    async def get_owned(
        self, session_id: UUID, user_id: UUID
    ) -> CoachingSession | None:
        session = self.sessions.get(session_id)
        return session if session and session.user_id == user_id else None

    async def list_for_user(
        self, user_id: UUID, limit: int = 50
    ) -> list[ConversationSummary]:
        self.listed_user_id = user_id
        return [
            ConversationSummary(
                session_id=item.id,
                title=item.title,
                created_at=item.created_at,
                updated_at=item.updated_at,
                last_message_preview="A small next step",
            )
            for item in self.sessions.values()
            if item.user_id == user_id
        ][:limit]

    async def delete_owned(self, session_id: UUID, user_id: UUID) -> bool:
        session = await self.get_owned(session_id, user_id)
        if session is None:
            return False
        del self.sessions[session_id]
        self.deleted.append(session_id)
        return True


class HistoryMessageRepository(MessageRepository):
    def __init__(self) -> None:
        self.messages = [
            Message(SESSION_ID, MessageRole.USER, "I feel overloaded"),
            Message(SESSION_ID, MessageRole.ASSISTANT, "What can wait until tomorrow?"),
        ]

    async def add(
        self,
        session_id: UUID,
        role: MessageRole,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> Message:
        raise AssertionError("Not used by history")

    async def list_recent(
        self,
        session_id: UUID,
        limit: int,
        *,
        exclude_message_id: UUID | None = None,
    ) -> list[Message]:
        raise AssertionError("Not used by history")

    async def list_for_session(self, session_id: UUID) -> list[Message]:
        return [item for item in self.messages if item.session_id == session_id]


def build_service() -> tuple[
    ConversationHistoryService, HistorySessionRepository, HistoryMessageRepository
]:
    sessions = HistorySessionRepository()
    messages = HistoryMessageRepository()
    return ConversationHistoryService(sessions, messages), sessions, messages


def test_listing_is_scoped_to_authenticated_user() -> None:
    service, sessions, _ = build_service()
    result = asyncio.run(service.list_conversations(USER_ID))
    assert sessions.listed_user_id == USER_ID
    assert [item.session_id for item in result] == [SESSION_ID]


def test_retrieving_owned_conversation_returns_ordered_messages() -> None:
    service, _, _ = build_service()
    result = asyncio.run(service.get_conversation(SESSION_ID, USER_ID))
    assert result.session.id == SESSION_ID
    assert [item.role for item in result.messages] == [
        MessageRole.USER,
        MessageRole.ASSISTANT,
    ]


def test_retrieving_another_users_conversation_is_rejected() -> None:
    service, _, _ = build_service()
    with pytest.raises(ConversationHistoryNotFoundError):
        asyncio.run(service.get_conversation(SESSION_ID, OTHER_USER_ID))


def test_deleting_owned_conversation() -> None:
    service, sessions, _ = build_service()
    asyncio.run(service.delete_conversation(SESSION_ID, USER_ID))
    assert sessions.deleted == [SESSION_ID]
    assert SESSION_ID not in sessions.sessions


def test_history_routes_are_authenticated_and_return_public_contract() -> None:
    service, _, _ = build_service()
    client = TestClient(app)
    assert client.get("/api/conversations").status_code == 401

    app.dependency_overrides[get_current_user] = lambda: USER
    app.dependency_overrides[get_conversation_history_service] = lambda: service
    try:
        listed = client.get(
            "/api/conversations",
            headers={"Authorization": "Bearer signed-test-token"},
        )
        detail = client.get(
            f"/api/conversations/{SESSION_ID}",
            headers={"Authorization": "Bearer signed-test-token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert listed.status_code == 200
    assert listed.json()[0]["session_id"] == str(SESSION_ID)
    assert "user_id" not in listed.json()[0]
    assert detail.status_code == 200
    assert [item["role"] for item in detail.json()["messages"]] == [
        "user",
        "assistant",
    ]


def test_history_route_hides_foreign_session() -> None:
    service, _, _ = build_service()
    foreign_user = User(
        id=OTHER_USER_ID,
        email="other@example.com",
        hashed_password="not-serialized",
        full_name=None,
        is_active=True,
        created_at=NOW,
        updated_at=NOW,
    )
    app.dependency_overrides[get_current_user] = lambda: foreign_user
    app.dependency_overrides[get_conversation_history_service] = lambda: service
    try:
        response = TestClient(app).get(
            f"/api/conversations/{SESSION_ID}",
            headers={"Authorization": "Bearer signed-test-token"},
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 404


def test_delete_history_route_returns_no_content() -> None:
    service, _, _ = build_service()
    app.dependency_overrides[get_current_user] = lambda: USER
    app.dependency_overrides[get_conversation_history_service] = lambda: service
    try:
        response = TestClient(app).delete(
            f"/api/conversations/{SESSION_ID}",
            headers={"Authorization": "Bearer signed-test-token"},
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 204
    assert response.content == b""
