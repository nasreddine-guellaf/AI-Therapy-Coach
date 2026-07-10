from dataclasses import dataclass, field
from uuid import UUID, uuid4

@dataclass(slots=True)
class Document:
    filename: str
    id: UUID = field(default_factory=uuid4)
    status: str = "pending"
