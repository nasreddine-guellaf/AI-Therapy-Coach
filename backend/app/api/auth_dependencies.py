"""FastAPI authentication composition and bearer-token dependencies."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import Argon2PasswordHasher, JWTAccessTokenManager
from app.domain.entities.user import User
from app.domain.services.auth_service import (
    AuthenticationUnavailableError,
    AuthService,
    InactiveUserError,
    InvalidCredentialsError,
)
from app.infrastructure.database.postgres import get_database_session
from app.infrastructure.database.user_repository import PostgreSQLUserRepository


bearer_scheme = HTTPBearer(auto_error=False)
password_hasher = Argon2PasswordHasher()
token_manager = JWTAccessTokenManager(
    secret_key=settings.secret_key,
    expire_minutes=settings.access_token_expire_minutes,
)


def get_auth_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> AuthService:
    """Compose authentication with a request-scoped PostgreSQL repository."""
    return AuthService(
        users=PostgreSQLUserRepository(session),
        password_hasher=password_hasher,
        token_manager=token_manager,
    )


async def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> User:
    """Resolve an active user from a Bearer token without trusting client IDs."""
    if credentials is None or credentials.scheme.casefold() != "bearer":
        raise _unauthorized()
    try:
        return await auth_service.current_user(credentials.credentials)
    except (InvalidCredentialsError, InactiveUserError) as error:
        raise _unauthorized() from error
    except AuthenticationUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is temporarily unavailable.",
        ) from error


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
