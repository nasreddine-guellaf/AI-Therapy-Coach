"""Tests for rate-limit-only LLM provider fallback composition."""

import asyncio

import pytest

from app.domain.interfaces.llm_provider import (
    LLMProvider,
    LLMPrompt,
    LLMRateLimitError,
    LLMServiceUnavailableError,
)
from app.infrastructure.llm.fallback_provider import RateLimitFallbackLLMProvider


PROMPT = LLMPrompt(
    instructions="Private system instructions",
    input="Private user message",
)


class StubProvider(LLMProvider):
    def __init__(self, result: str | BaseException) -> None:
        self.result = result
        self.calls = 0
        self.received_prompt: LLMPrompt | None = None

    async def generate(self, prompt: LLMPrompt) -> str:
        self.calls += 1
        self.received_prompt = prompt
        if isinstance(self.result, BaseException):
            raise self.result
        return self.result


def _provider(
    primary: StubProvider,
    fallback: StubProvider,
) -> RateLimitFallbackLLMProvider:
    return RateLimitFallbackLLMProvider(
        primary,
        fallback,
        primary_name="gemini",
        fallback_name="openrouter",
    )


def test_primary_response_does_not_call_fallback() -> None:
    primary = StubProvider("Gemini answer")
    fallback = StubProvider("OpenRouter answer")

    result = asyncio.run(_provider(primary, fallback).generate(PROMPT))

    assert result == "Gemini answer"
    assert primary.calls == 1
    assert fallback.calls == 0


def test_rate_limit_calls_openrouter_with_same_prompt(caplog) -> None:
    primary = StubProvider(LLMRateLimitError())
    fallback = StubProvider("OpenRouter answer")

    result = asyncio.run(_provider(primary, fallback).generate(PROMPT))

    assert result == "OpenRouter answer"
    assert fallback.calls == 1
    assert fallback.received_prompt is PROMPT
    assert "primary=gemini" in caplog.text
    assert "fallback=openrouter" in caplog.text
    assert "error_type=LLMRateLimitError" in caplog.text
    assert "Private system instructions" not in caplog.text
    assert "Private user message" not in caplog.text


def test_non_rate_limit_failure_does_not_call_fallback() -> None:
    primary = StubProvider(LLMServiceUnavailableError())
    fallback = StubProvider("OpenRouter answer")

    with pytest.raises(LLMServiceUnavailableError):
        asyncio.run(_provider(primary, fallback).generate(PROMPT))

    assert fallback.calls == 0


def test_fallback_failure_remains_a_safe_domain_error() -> None:
    primary = StubProvider(LLMRateLimitError())
    fallback = StubProvider(LLMServiceUnavailableError())

    with pytest.raises(LLMServiceUnavailableError):
        asyncio.run(_provider(primary, fallback).generate(PROMPT))
