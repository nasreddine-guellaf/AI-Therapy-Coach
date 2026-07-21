"""Framework-independent authentication application service."""

from dataclasses import dataclass

from app.domain.entities.user import User
from app.domain.interfaces.auth import (
    AccessTokenManager,
    PasswordHasher,
    UserAlreadyExistsError,
    UserRepository,
    UserRepositoryError,
)


class AuthenticationError(RuntimeError):
    """Base expected authentication failure."""


class EmailAlreadyRegisteredError(AuthenticationError):
    """Raised when registration uses an existing normalized email."""


class InvalidCredentialsError(AuthenticationError):
    """Raised for invalid credentials or invalid access tokens."""


class InactiveUserError(AuthenticationError):
    """Raised when a valid identity is not allowed to sign in."""


class AuthenticationUnavailableError(AuthenticationError):
    """Raised when secure token configuration or persistence is unavailable."""


@dataclass(frozen=True, slots=True)
class AuthenticatedSession:
    user: User
    access_token: str


class AuthService:
    """Register, authenticate, and resolve users through domain ports."""

    def __init__(
        self,
        *,
        users: UserRepository,
        password_hasher: PasswordHasher,
        token_manager: AccessTokenManager,
    ) -> None:
        self.users = users
        self.password_hasher = password_hasher
        self.token_manager = token_manager

    async def register(
        self, *, email: str, password: str, full_name: str | None
    ) -> User:
        normalized_email = self._normalize_email(email)
        normalized_name = full_name.strip() if full_name and full_name.strip() else None
        try:
            if await self.users.get_by_email(normalized_email):
                raise EmailAlreadyRegisteredError
            return await self.users.create(
                email=normalized_email,
                hashed_password=self.password_hasher.hash(password),
                full_name=normalized_name,
            )
        except UserAlreadyExistsError as error:
            raise EmailAlreadyRegisteredError from error
        except UserRepositoryError as error:
            raise AuthenticationUnavailableError from error

    async def login(self, *, email: str, password: str) -> AuthenticatedSession:
        normalized_email = self._normalize_email(email)
        try:
            user = await self.users.get_by_email(normalized_email)
        except UserRepositoryError as error:
            raise AuthenticationUnavailableError from error

        candidate_hash = user.hashed_password if user else self.password_hasher.dummy_hash
        try:
            password_is_valid = self.password_hasher.verify(password, candidate_hash)
        except Exception as error:
            # A corrupted or unsupported stored hash is an internal failure, not
            # an authentication detail that should be exposed to the caller.
            raise AuthenticationUnavailableError from error
        if user is None or not password_is_valid:
            raise InvalidCredentialsError
        if not user.is_active:
            raise InactiveUserError

        try:
            token = self.token_manager.create(user.id)
        except RuntimeError as error:
            raise AuthenticationUnavailableError from error
        return AuthenticatedSession(user=user, access_token=token)

    async def current_user(self, token: str) -> User:
        try:
            user_id = self.token_manager.decode_subject(token)
            user = await self.users.get_by_id(user_id)
        except UserRepositoryError as error:
            raise AuthenticationUnavailableError from error
        except (RuntimeError, ValueError) as error:
            raise InvalidCredentialsError from error

        if user is None:
            raise InvalidCredentialsError
        if not user.is_active:
            raise InactiveUserError
        return user

    @staticmethod
    def _normalize_email(email: str) -> str:
        return email.strip().casefold()
