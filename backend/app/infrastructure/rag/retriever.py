from app.domain.interfaces.vector_store import VectorStore

class Retriever:
    def __init__(self, store: VectorStore) -> None:
        self.store = store

    async def retrieve(self, query_vector: list[float], limit: int = 5) -> list[dict]:
        return await self.store.search(query_vector, limit)
