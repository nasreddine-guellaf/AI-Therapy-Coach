class MemoryService:
    """Port-neutral conversation memory policy."""
    async def recent_context(self, session_id: str, limit: int = 10) -> list[str]:
        # TODO: retrieve through an injected repository.
        return []
