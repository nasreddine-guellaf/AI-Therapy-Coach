from abc import ABC, abstractmethod
from typing import Sequence

class VectorStore(ABC):
    @abstractmethod
    async def upsert(self, ids: Sequence[str], vectors: Sequence[Sequence[float]], payloads: Sequence[dict]) -> None: ...
    @abstractmethod
    async def search(self, vector: Sequence[float], limit: int = 5) -> list[dict]: ...
