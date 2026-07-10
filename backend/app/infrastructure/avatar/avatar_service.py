class AvatarService:
    """Coordinates lip-sync/avatar rendering through a future isolated provider."""
    async def render(self, audio: bytes) -> str:
        raise NotImplementedError("TODO: select an avatar provider and return a job ID")
