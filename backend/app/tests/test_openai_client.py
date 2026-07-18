"""Unit tests for the OpenAI adapter without making network requests."""

import asyncio
from types import SimpleNamespace

import httpx
import openai
import pytest

from app.domain.interfaces.llm_provider import (
    LLMNotConfiguredError,
    LLMPrompt,
    LLMServiceUnavailableError,
)
from app.infrastructure.llm.openai_client import OpenAILLMProvider


class FakeResponsesAPI:
    def __init__(self, output_text: str) -> None:
        self.output_text = output_text
        self.request: dict[str, object] = {}

    async def create(self, **kwargs: object) -> object:
        self.request = kwargs
        return SimpleNamespace(output_text=self.output_text)


class FakeOpenAIClient:
    def __init__(self, output_text: str) -> None:
        self.responses = FakeResponsesAPI(output_text)


class FailingResponsesAPI:
    async def create(self, **kwargs: object) -> object:
        raise openai.APIConnectionError(
            request=httpx.Request("POST", "https://api.openai.com/v1/responses")
        )


class FailingOpenAIClient:
    responses = FailingResponsesAPI()


def test_openai_provider_maps_domain_prompt_to_responses_api() -> None:
    client = FakeOpenAIClient("  A calm, reflective response.  ")
    provider = OpenAILLMProvider(
        api_key=None,
        model="test-model",
        max_output_tokens=321,
        client=client,
    )
    prompt = LLMPrompt(instructions="Stay in scope.", input="User message")

    result = asyncio.run(provider.generate(prompt))

    assert result == "A calm, reflective response."
    assert client.responses.request == {
        "model": "test-model",
        "instructions": "Stay in scope.",
        "input": "User message",
        "max_output_tokens": 321,
    }


def test_openai_provider_does_not_create_a_client_without_api_key() -> None:
    provider = OpenAILLMProvider(api_key=None, model="test-model")
    assert not provider.is_configured

    with pytest.raises(LLMNotConfiguredError):
        asyncio.run(
            provider.generate(LLMPrompt(instructions="Safe.", input="Hello"))
        )


def test_openai_provider_logs_only_safe_error_type(caplog) -> None:
    provider = OpenAILLMProvider(
        api_key=None,
        model="test-model",
        client=FailingOpenAIClient(),
    )

    with pytest.raises(LLMServiceUnavailableError):
        asyncio.run(
            provider.generate(LLMPrompt(instructions="Safe.", input="Hello"))
        )

    assert "provider=openai" in caplog.text
    assert "error_type=APIConnectionError" in caplog.text
    assert "Safe." not in caplog.text
    assert "Hello" not in caplog.text
