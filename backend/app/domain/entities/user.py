from dataclasses import dataclass
from uuid import UUID, uuid4

@dataclass(slots=True)
class User:
    id: UUID
    display_name: str

    @classmethod
    def create(cls, display_name: str) -> "User":
        return cls(uuid4(), display_name)
