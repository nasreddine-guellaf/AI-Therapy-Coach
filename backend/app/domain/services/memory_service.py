class MemoryService:
    """Conversation memory policy awaiting an injected repository."""

    async def recent_context(
        self, session_id: str | None, limit: int = 10
    ) -> list[str]:
        """Return recent, authorized context for a session.

        The initial implementation is intentionally empty until a repository
        port and explicit memory consent rules are implemented.
        """
        # TODO: retrieve through an injected repository.
        return []
