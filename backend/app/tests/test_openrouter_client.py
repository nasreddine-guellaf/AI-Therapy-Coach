"""Unit tests for the OpenRouter adapter without making network requests."""

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
from app.infrastructure.llm.openrouter_client import OpenRouterLLMProvider


class FakeChatCompletionsAPI:
    def __init__(self, content: str) -> None:
        self.content = content
        self.request: dict[str, object] = {}

    async def create(self, **kwargs: object) -> object:
        self.request = kwargs
        message = SimpleNamespace(content=self.content)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class FakeOpenRouterClient:
    def __init__(self, content: str) -> None:
        completions = FakeChatCompletionsAPI(content)
        self.chat = SimpleNamespace(completions=completions)


class FailingChatCompletionsAPI:
    async def create(self, **kwargs: object) -> object:
        raise openai.APIConnectionError(
            request=httpx.Request(
                "POST", "https://openrouter.ai/api/v1/chat/completions"
            )
        )


class FailingOpenRouterClient:
    chat = SimpleNamespace(completions=FailingChatCompletionsAPI())


def test_openrouter_provider_maps_prompt_to_chat_completions() -> None:
    client = FakeOpenRouterClient("  A measured response.  ")
    provider = OpenRouterLLMProvider(
        api_key=None,
        base_url="https://openrouter.ai/api/v1",
        model="test-model",
        max_output_tokens=321,
        client=client,
    )
    prompt = LLMPrompt(instructions="Stay in scope.", input="User message")

    result = asyncio.run(provider.generate(prompt))

    assert result == "A measured response."
    assert client.chat.completions.request == {
        "model": "test-model",
        "messages": [
            {"role": "system", "content": "Stay in scope."},
            {"role": "user", "content": "User message"},
        ],
        "max_tokens": 321,
    }


def test_openrouter_provider_does_not_create_client_without_api_key() -> None:
    provider = OpenRouterLLMProvider(
        api_key=None,
        base_url="https://openrouter.ai/api/v1",
        model="test-model",
    )
    assert not provider.is_configured

    with pytest.raises(LLMNotConfiguredError):
        asyncio.run(
            provider.generate(LLMPrompt(instructions="Safe.", input="Hello"))
        )


def test_openrouter_provider_logs_only_safe_error_type(caplog) -> None:
    provider = OpenRouterLLMProvider(
        api_key=None,
        base_url="https://openrouter.ai/api/v1",
        model="test-model",
        client=FailingOpenRouterClient(),
    )

    with pytest.raises(LLMServiceUnavailableError):
        asyncio.run(
            provider.generate(LLMPrompt(instructions="Safe.", input="Hello"))
        )

    assert "provider=openrouter" in caplog.text
    assert "error_type=APIConnectionError" in caplog.text
    assert "Safe." not in caplog.text
    assert "Hello" not in caplog.text
