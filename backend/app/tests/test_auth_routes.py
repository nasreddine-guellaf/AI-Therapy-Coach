"""HTTP contract tests for authentication and protected conversation routes."""

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import UUID

from fastapi.testclient import TestClient

from app.api.auth_dependencies import get_auth_service, get_current_user
from app.api.dependencies import get_conversation_manager
from app.domain.entities.user import User
from app.domain.services.auth_service import (
    AuthenticatedSession,
    InvalidCredentialsError,
)
from app.main import app


USER_ID = UUID("00000000-0000-0000-0000-000000000001")
NOW = datetime.now(timezone.utc)
USER = User(
    id=USER_ID,
    email="person@example.com",
    hashed_password="not-serialized",
    full_name="Test Person",
    is_active=True,
    created_at=NOW,
    updated_at=NOW,
)


class FakeAuthService:
    async def register(self, **kwargs) -> User:
        return USER

    async def login(self, **kwargs) -> AuthenticatedSession:
        if kwargs["password"] == "wrong-password":
            raise InvalidCredentialsError
        return AuthenticatedSession(user=USER, access_token="signed-test-token")


class FakeConversationManager:
    command = None

    async def handle(self, command):
        self.command = command
        return SimpleNamespace(
            message="A safe response.",
            status="completed",
            memory_items_used=0,
            rag_chunks_used=0,
            source_ids=[],
        )


def test_register_and_login_contracts() -> None:
    app.dependency_overrides[get_auth_service] = lambda: FakeAuthService()
    client = TestClient(app)
    try:
        registered = client.post(
            "/api/auth/register",
            json={
                "email": "person@example.com",
                "password": "safe-password-123",
                "full_name": "Test Person",
            },
        )
        logged_in = client.post(
            "/api/auth/login",
            json={
                "email": "person@example.com",
                "password": "safe-password-123",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert registered.status_code == 201
    assert "hashed_password" not in registered.json()
    assert logged_in.status_code == 200
    assert logged_in.json()["access_token"] == "signed-test-token"


def test_invalid_login_is_unauthorized() -> None:
    app.dependency_overrides[get_auth_service] = lambda: FakeAuthService()
    try:
        response = TestClient(app).post(
            "/api/auth/login",
            json={"email": "person@example.com", "password": "wrong-password"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid email or password."}


def test_conversation_requires_a_bearer_token() -> None:
    response = TestClient(app).post(
        "/api/conversation/message", json={"message": "I feel tense"}
    )
    assert response.status_code == 401


def test_authenticated_conversation_uses_jwt_user_not_request_user_id() -> None:
    manager = FakeConversationManager()
    app.dependency_overrides[get_current_user] = lambda: USER
    app.dependency_overrides[get_conversation_manager] = lambda: manager
    try:
        response = TestClient(app).post(
            "/api/conversation/message",
            headers={"Authorization": "Bearer signed-test-token"},
            json={"message": "I feel tense"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 202
    assert manager.command.user_id == USER_ID
