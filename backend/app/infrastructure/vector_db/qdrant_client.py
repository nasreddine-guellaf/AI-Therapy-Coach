from typing import Sequence
from app.domain.interfaces.vector_store import VectorStore

class QdrantVectorStore(VectorStore):
    """Qdrant adapter placeholder; performs no network calls."""
    async def upsert(self, ids: Sequence[str], vectors: Sequence[Sequence[float]], payloads: Sequence[dict]) -> None:
        raise NotImplementedError("TODO: configure the Qdrant SDK")
    async def search(self, vector: Sequence[float], limit: int = 5) -> list[dict]:
        raise NotImplementedError("TODO: configure the Qdrant SDK")
