from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Provider-neutral port for text generation."""

    @abstractmethod
    async def generate(self, prompt: str) -> str:
        """Generate one response from a fully constructed prompt."""
        raise NotImplementedError
