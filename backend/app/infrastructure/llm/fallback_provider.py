"""Provider-neutral primary/fallback composition for language generation."""

import logging

from app.domain.interfaces.llm_provider import (
    LLMProvider,
    LLMPrompt,
    LLMRateLimitError,
)


logger = logging.getLogger(__name__)


class RateLimitFallbackLLMProvider(LLMProvider):
    """Use a secondary provider only when the primary reaches its rate limit.

    The same provider-neutral prompt is passed to both adapters. Prompt content,
    generated text, credentials, and raw provider exceptions are never logged.
    """

    def __init__(
        self,
        primary: LLMProvider,
        fallback: LLMProvider,
        *,
        primary_name: str,
        fallback_name: str,
    ) -> None:
        self.primary = primary
        self.fallback = fallback
        self.primary_name = primary_name
        self.fallback_name = fallback_name

    async def generate(self, prompt: LLMPrompt) -> str:
        try:
            return await self.primary.generate(prompt)
        except LLMRateLimitError:
            logger.warning(
                "LLM fallback activated: primary=%s fallback=%s "
                "error_type=LLMRateLimitError",
                self.primary_name,
                self.fallback_name,
            )
            return await self.fallback.generate(prompt)
