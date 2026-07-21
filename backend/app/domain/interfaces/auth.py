"""Provider-neutral authentication ports and repository errors."""

from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities.user import User


class UserRepositoryError(RuntimeError):
    """Base persistence error that does not expose database details."""


class UserAlreadyExistsError(UserRepositoryError):
    """Raised when a normalized email already belongs to a user."""


class UserRepository(ABC):
    """Persistence port required by authentication use cases."""

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> User | None:
        raise NotImplementedError

    @abstractmethod
    async def create(
        self,
        *,
        email: str,
        hashed_password: str,
        full_name: str | None,
    ) -> User:
        raise NotImplementedError


class PasswordHasher(ABC):
    """Password hashing port implemented by a secure external algorithm."""

    @property
    @abstractmethod
    def dummy_hash(self) -> str:
        """Return a non-user hash used to reduce email enumeration timing."""
        raise NotImplementedError

    @abstractmethod
    def hash(self, password: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def verify(self, password: str, hashed_password: str) -> bool:
        raise NotImplementedError


class AccessTokenManager(ABC):
    """Signed access-token port with no JWT dependency in the domain."""

    @abstractmethod
    def create(self, user_id: UUID) -> str:
        raise NotImplementedError

    @abstractmethod
    def decode_subject(self, token: str) -> UUID:
        raise NotImplementedError
