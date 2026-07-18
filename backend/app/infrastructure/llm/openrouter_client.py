"""OpenRouter implementation of the domain language-model provider port."""

import logging
from typing import Protocol

import openai
from openai import AsyncOpenAI

from app.domain.interfaces.llm_provider import (
    LLMInvalidResponseError,
    LLMNotConfiguredError,
    LLMPrompt,
    LLMProvider,
    LLMServiceUnavailableError,
)


logger = logging.getLogger(__name__)


class _ChatCompletionsAPI(Protocol):
    async def create(self, **kwargs: object) -> object: ...


class _ChatAPI(Protocol):
    completions: _ChatCompletionsAPI


class _OpenRouterClient(Protocol):
    chat: _ChatAPI


class OpenRouterLLMProvider(LLMProvider):
    """Generate text through OpenRouter's OpenAI-compatible Chat API.

    Credentials and endpoint configuration are supplied by the application
    composition root. Request content and raw provider errors are never logged
    or returned to callers.
    """

    def __init__(
        self,
        *,
        api_key: str | None,
        base_url: str,
        model: str,
        timeout_seconds: float = 30.0,
        max_output_tokens: int = 700,
        client: _OpenRouterClient | None = None,
    ) -> None:
        self.api_key = api_key.strip() if api_key else None
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.max_output_tokens = max_output_tokens
        self._client = client

        if self._client is None and self.api_key:
            self._client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=timeout_seconds,
                max_retries=2,
            )

    @property
    def is_configured(self) -> bool:
        """Return whether generation can be attempted without exposing the key."""
        return self._client is not None

    async def generate(self, prompt: LLMPrompt) -> str:
        """Map a provider-neutral prompt to one Chat Completions request."""
        if self._client is None:
            self._log_error_type(LLMNotConfiguredError)
            raise LLMNotConfiguredError

        try:
            completion = await self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": prompt.instructions},
                    {"role": "user", "content": prompt.input},
                ],
                max_tokens=self.max_output_tokens,
            )
        except openai.AuthenticationError as error:
            self._log_error_type(type(error))
            raise LLMServiceUnavailableError from error
        except openai.RateLimitError as error:
            self._log_error_type(type(error))
            raise LLMServiceUnavailableError from error
        except (openai.APIConnectionError, openai.APITimeoutError) as error:
            self._log_error_type(type(error))
            raise LLMServiceUnavailableError from error
        except openai.APIError as error:
            self._log_error_type(type(error))
            raise LLMServiceUnavailableError from error

        # TODO: add privacy-reviewed usage metrics, provider routing metadata,
        # request IDs, and model availability monitoring before production.
        choices = getattr(completion, "choices", None)
        if not choices:
            self._log_error_type(LLMInvalidResponseError)
            raise LLMInvalidResponseError
        message = getattr(choices[0], "message", None)
        content = getattr(message, "content", None)
        if not isinstance(content, str) or not content.strip():
            self._log_error_type(LLMInvalidResponseError)
            raise LLMInvalidResponseError
        return content.strip()

    @staticmethod
    def _log_error_type(error_type: type[BaseException]) -> None:
        """Log safe diagnostic metadata without exception details or prompts."""
        logger.warning(
            "LLM provider failure: provider=openrouter error_type=%s",
            error_type.__name__,
        )
