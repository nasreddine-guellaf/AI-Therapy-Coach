"""Authentication service tests using an in-memory repository fake."""

import asyncio
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from app.core.security import Argon2PasswordHasher, JWTAccessTokenManager
from app.domain.entities.user import User
from app.domain.interfaces.auth import UserRepository
from app.domain.services.auth_service import AuthService, InvalidCredentialsError


class FakeUserRepository(UserRepository):
    def __init__(self) -> None:
        self.users: dict[UUID, User] = {}

    async def get_by_email(self, email: str) -> User | None:
        return next((user for user in self.users.values() if user.email == email), None)

    async def get_by_id(self, user_id: UUID) -> User | None:
        return self.users.get(user_id)

    async def create(
        self,
        *,
        email: str,
        hashed_password: str,
        full_name: str | None,
    ) -> User:
        now = datetime.now(timezone.utc)
        user = User(
            id=uuid4(),
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        self.users[user.id] = user
        return user


def build_service() -> tuple[AuthService, FakeUserRepository]:
    users = FakeUserRepository()
    service = AuthService(
        users=users,
        password_hasher=Argon2PasswordHasher(),
        token_manager=JWTAccessTokenManager(
            secret_key="test-secret-key-that-is-at-least-32-bytes-long",
            expire_minutes=30,
        ),
    )
    return service, users


def test_register_hashes_password_and_normalizes_email() -> None:
    service, _ = build_service()

    user = asyncio.run(
        service.register(
            email=" Person@Example.COM ",
            password="safe-password-123",
            full_name=" Test Person ",
        )
    )

    assert user.email == "person@example.com"
    assert user.full_name == "Test Person"
    assert user.hashed_password != "safe-password-123"
    assert user.hashed_password.startswith("$argon2")


def test_login_returns_a_token_resolving_to_the_user() -> None:
    service, _ = build_service()
    registered = asyncio.run(
        service.register(
            email="person@example.com",
            password="safe-password-123",
            full_name=None,
        )
    )

    authenticated = asyncio.run(
        service.login(email="person@example.com", password="safe-password-123")
    )
    current = asyncio.run(service.current_user(authenticated.access_token))

    assert authenticated.user.id == registered.id
    assert current.id == registered.id


def test_invalid_login_returns_one_generic_error() -> None:
    service, _ = build_service()

    with pytest.raises(InvalidCredentialsError):
        asyncio.run(
            service.login(email="missing@example.com", password="wrong-password")
        )
