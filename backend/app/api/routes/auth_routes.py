"""Thin HTTP routes for registration, login, and current-user lookup."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.auth_dependencies import get_auth_service, get_current_user
from app.domain.entities.user import User
from app.domain.services.auth_service import (
    AuthenticationUnavailableError,
    AuthService,
    EmailAlreadyRegisteredError,
    InactiveUserError,
    InvalidCredentialsError,
)
from app.schemas.auth_schema import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    UserResponse,
)


router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserResponse:
    try:
        user = await auth_service.register(
            email=str(request.email),
            password=request.password,
            full_name=request.full_name,
        )
    except EmailAlreadyRegisteredError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        ) from error
    except AuthenticationUnavailableError as error:
        raise _service_unavailable() from error
    return UserResponse.model_validate(user)


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> LoginResponse:
    try:
        authenticated = await auth_service.login(
            email=str(request.email), password=request.password
        )
    except (InvalidCredentialsError, InactiveUserError) as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error
    except AuthenticationUnavailableError as error:
        raise _service_unavailable() from error
    return LoginResponse(
        access_token=authenticated.access_token,
        user=UserResponse.model_validate(authenticated.user),
    )


@router.get("/me", response_model=UserResponse)
async def me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserResponse:
    return UserResponse.model_validate(current_user)


def _service_unavailable() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Authentication service is temporarily unavailable.",
    )
