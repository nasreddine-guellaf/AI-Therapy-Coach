"""Authentication-ready user domain entity."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(slots=True)
class User:
    """Application user without framework or persistence dependencies."""

    id: UUID
    email: str
    hashed_password: str
    full_name: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
