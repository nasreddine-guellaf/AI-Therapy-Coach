class EmbeddingService:
    async def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError("TODO: inject an embedding provider")
