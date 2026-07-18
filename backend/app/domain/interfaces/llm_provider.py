"""Provider-neutral contracts and errors for language-model generation."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LLMPrompt:
    """Separate application instructions from dynamic conversation input."""

    instructions: str
    input: str


class LLMProviderError(RuntimeError):
    """Base error safe for the application layer to handle generically."""

    user_message = "The AI service is temporarily unavailable. Please try again later."


class LLMNotConfiguredError(LLMProviderError):
    """Raised when no provider credential is configured."""

    user_message = (
        "The selected AI provider is not configured. Add its API key to the "
        "backend environment to enable generated coaching responses."
    )


class LLMServiceUnavailableError(LLMProviderError):
    """Raised for provider connectivity, timeout, quota, or API failures."""


class LLMInvalidResponseError(LLMProviderError):
    """Raised when the provider returns no usable assistant text."""

    user_message = "The AI service returned no usable response. Please try again."


class LLMProvider(ABC):
    """Provider-neutral port for text generation."""

    @abstractmethod
    async def generate(self, prompt: LLMPrompt) -> str:
        """Generate one assistant response from a structured prompt."""
        raise NotImplementedError
