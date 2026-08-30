"""Gemini implementation of the domain language-model provider port."""

import logging
from collections.abc import Sequence
from typing import Protocol

import openai
from openai import AsyncOpenAI

from app.domain.interfaces.llm_provider import (
    LLMIncompleteResponseError,
    LLMInvalidResponseError,
    LLMNotConfiguredError,
    LLMPrompt,
    LLMProvider,
    LLMRateLimitError,
    LLMServiceUnavailableError,
)


logger = logging.getLogger(__name__)


class _ChatCompletionsAPI(Protocol):
    async def create(self, **kwargs: object) -> object: ...


class _ChatAPI(Protocol):
    completions: _ChatCompletionsAPI


class _GeminiClient(Protocol):
    chat: _ChatAPI


class GeminiLLMProvider(LLMProvider):
    """Generate text through Gemini's OpenAI-compatible Chat API.

    The adapter translates provider-neutral prompts at the infrastructure
    boundary. Credentials, prompts, response bodies, and provider exception
    details are never logged or returned to delivery adapters.
    """

    def __init__(
        self,
        *,
        api_key: str | None,
        base_url: str,
        model: str,
        timeout_seconds: float = 30.0,
        max_output_tokens: int = 1200,
        client: _GeminiClient | None = None,
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
        """Map one domain prompt to Gemini Chat Completions."""
        if self._client is None:
            self._log_error_type(LLMNotConfiguredError)
            raise LLMNotConfiguredError

        completion = await self._create_completion(prompt, self.max_output_tokens)
        content, finish_reason, output_tokens = self._read_completion(completion)
        self._log_response_metadata(finish_reason, not bool(content), output_tokens)

        if self._is_truncated(finish_reason):
            retry_limit = self.max_output_tokens * 2
            completion = await self._create_completion(prompt, retry_limit)
            content, finish_reason, output_tokens = self._read_completion(completion)
            self._log_response_metadata(finish_reason, not bool(content), output_tokens)
            if self._is_truncated(finish_reason):
                self._log_error_type(LLMIncompleteResponseError)
                raise LLMIncompleteResponseError

        if not content:
            self._log_error_type(LLMInvalidResponseError)
            raise LLMInvalidResponseError
        return content

    async def _create_completion(
        self,
        prompt: LLMPrompt,
        max_output_tokens: int,
    ) -> object:
        """Call Gemini without logging any prompt or response content."""
        assert self._client is not None
        try:
            return await self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": prompt.instructions},
                    {"role": "user", "content": prompt.input},
                ],
                max_completion_tokens=max_output_tokens,
            )
        except openai.AuthenticationError as error:
            self._log_error_type(type(error))
            raise LLMServiceUnavailableError from error
        except openai.RateLimitError as error:
            self._log_error_type(type(error))
            raise LLMRateLimitError from error
        except (openai.APIConnectionError, openai.APITimeoutError) as error:
            self._log_error_type(type(error))
            raise LLMServiceUnavailableError from error
        except openai.APIError as error:
            self._log_error_type(type(error))
            raise LLMServiceUnavailableError from error

    @classmethod
    def _read_completion(
        cls,
        completion: object,
    ) -> tuple[str, str | None, int | None]:
        """Extract all compatible text parts plus safe completion metadata."""
        choices = getattr(completion, "choices", None)
        if not choices:
            return "", None, cls._output_token_count(completion)
        choice = choices[0]
        finish_reason = cls._normalize_finish_reason(
            getattr(choice, "finish_reason", None)
        )
        message = getattr(choice, "message", None)
        content = getattr(message, "content", None)
        return (
            cls._extract_content(content),
            finish_reason,
            cls._output_token_count(completion),
        )

    @staticmethod
    def _extract_content(content: object) -> str:
        """Support Gemini content as a string or a list of text parts."""
        if isinstance(content, str):
            return content.strip()
        if not isinstance(content, Sequence) or isinstance(
            content, (str, bytes, bytearray)
        ):
            return ""

        parts: list[str] = []
        for part in content:
            text = (
                part.get("text")
                if isinstance(part, dict)
                else getattr(part, "text", None)
            )
            if isinstance(text, str) and text.strip():
                parts.append(text.strip())
        return "\n".join(parts).strip()

    @staticmethod
    def _normalize_finish_reason(value: object) -> str | None:
        normalized = getattr(value, "value", value)
        return (
            str(normalized).strip().lower()
            if normalized is not None
            else None
        )

    @staticmethod
    def _is_truncated(finish_reason: str | None) -> bool:
        return finish_reason in {"length", "max_tokens", "max_output_tokens"}

    @staticmethod
    def _output_token_count(completion: object) -> int | None:
        usage = getattr(completion, "usage", None)
        for field_name in ("completion_tokens", "output_tokens"):
            value = (
                usage.get(field_name)
                if isinstance(usage, dict)
                else getattr(usage, field_name, None)
            )
            if isinstance(value, int) and not isinstance(value, bool):
                return value
        return None

    def _log_response_metadata(
        self,
        finish_reason: str | None,
        content_empty: bool,
        output_tokens: int | None,
    ) -> None:
        logger.info(
            "LLM provider response: provider=gemini model=%s finish_reason=%s "
            "content_empty=%s output_tokens=%s",
            self.model,
            finish_reason,
            content_empty,
            output_tokens,
        )

    def _log_error_type(self, error_type: type[BaseException]) -> None:
        """Log only approved provider metadata and exception class."""
        logger.warning(
            "LLM provider failure: provider=gemini model=%s error_type=%s",
            self.model,
            error_type.__name__,
        )
