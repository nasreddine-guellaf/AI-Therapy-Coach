"""Argon2 password hashing and signed JWT access-token adapters."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from jwt import InvalidTokenError
from pwdlib import PasswordHash

from app.domain.interfaces.auth import AccessTokenManager, PasswordHasher


class Argon2PasswordHasher(PasswordHasher):
    """Hash passwords using pwdlib's recommended Argon2 configuration."""

    def __init__(self) -> None:
        self._password_hash = PasswordHash.recommended()
        self._dummy_hash = self._password_hash.hash("not-a-real-user-password")

    @property
    def dummy_hash(self) -> str:
        return self._dummy_hash

    def hash(self, password: str) -> str:
        return self._password_hash.hash(password)

    def verify(self, password: str, hashed_password: str) -> bool:
        return self._password_hash.verify(password, hashed_password)


class JWTAccessTokenManager(AccessTokenManager):
    """Create and validate short-lived HS256 access tokens."""

    def __init__(self, *, secret_key: str | None, expire_minutes: int) -> None:
        self._secret_key = secret_key.strip() if secret_key else None
        self._expire_minutes = expire_minutes

    def create(self, user_id: UUID) -> str:
        secret = self._validated_secret()
        now = datetime.now(timezone.utc)
        return jwt.encode(
            {
                "sub": str(user_id),
                "iat": now,
                "exp": now + timedelta(minutes=self._expire_minutes),
            },
            secret,
            algorithm="HS256",
        )

    def decode_subject(self, token: str) -> UUID:
        secret = self._validated_secret()
        try:
            payload = jwt.decode(token, secret, algorithms=["HS256"])
            subject = payload.get("sub")
            if not isinstance(subject, str):
                raise ValueError("Token subject is missing")
            return UUID(subject)
        except InvalidTokenError as error:
            raise ValueError("Invalid access token") from error

    def _validated_secret(self) -> str:
        if self._secret_key is None or len(self._secret_key) < 32:
            raise RuntimeError("JWT secret is not configured securely")
        return self._secret_key
