"""Unit tests for Gemini's OpenAI-compatible adapter without network calls."""

import asyncio
from types import SimpleNamespace

import httpx
import openai
import pytest

from app.domain.interfaces.llm_provider import (
    LLMIncompleteResponseError,
    LLMInvalidResponseError,
    LLMNotConfiguredError,
    LLMPrompt,
    LLMRateLimitError,
    LLMServiceUnavailableError,
)
from app.infrastructure.llm.gemini_client import GeminiLLMProvider


GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
PROMPT = LLMPrompt(instructions="Stay in scope.", input="Private user message")


class FakeChatCompletionsAPI:
    def __init__(
        self,
        content: object,
        *,
        include_choice: bool = True,
        finish_reason: str = "stop",
        responses: list[object] | None = None,
    ) -> None:
        self.content = content
        self.include_choice = include_choice
        self.finish_reason = finish_reason
        self.responses = list(responses or [])
        self.request: dict[str, object] = {}
        self.requests: list[dict[str, object]] = []

    async def create(self, **kwargs: object) -> object:
        self.request = kwargs
        self.requests.append(kwargs)
        if self.responses:
            return self.responses.pop(0)
        if not self.include_choice:
            return SimpleNamespace(choices=[])
        message = SimpleNamespace(content=self.content)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=message,
                    finish_reason=self.finish_reason,
                )
            ],
            usage=SimpleNamespace(completion_tokens=42),
        )


class FakeGeminiClient:
    def __init__(self, content: object, *, include_choice: bool = True) -> None:
        self.completions = FakeChatCompletionsAPI(
            content,
            include_choice=include_choice,
        )
        self.chat = SimpleNamespace(completions=self.completions)


class FailingChatCompletionsAPI:
    def __init__(self, error: BaseException) -> None:
        self.error = error

    async def create(self, **kwargs: object) -> object:
        raise self.error


class FailingGeminiClient:
    def __init__(self, error: BaseException) -> None:
        self.chat = SimpleNamespace(
            completions=FailingChatCompletionsAPI(error)
        )


def _request() -> httpx.Request:
    return httpx.Request("POST", f"{GEMINI_URL}chat/completions")


def _response(status_code: int) -> httpx.Response:
    return httpx.Response(status_code, request=_request())


def test_gemini_provider_maps_prompt_to_chat_completions() -> None:
    client = FakeGeminiClient("  A grounded response.  ")
    provider = GeminiLLMProvider(
        api_key=None,
        base_url=GEMINI_URL,
        model="test-gemini-model",
        max_output_tokens=321,
        client=client,
    )

    result = asyncio.run(provider.generate(PROMPT))

    assert result == "A grounded response."
    assert client.completions.request == {
        "model": "test-gemini-model",
        "messages": [
            {"role": "system", "content": "Stay in scope."},
            {"role": "user", "content": "Private user message"},
        ],
        "max_completion_tokens": 321,
    }


def test_gemini_provider_extracts_all_content_parts() -> None:
    client = FakeGeminiClient(
        [
            {"type": "text", "text": "First practical step."},
            SimpleNamespace(type="text", text="Second practical step."),
            {"type": "image", "image_url": "ignored"},
        ]
    )
    provider = GeminiLLMProvider(
        api_key=None,
        base_url=GEMINI_URL,
        model="test-gemini-model",
        client=client,
    )

    result = asyncio.run(provider.generate(PROMPT))

    assert result == "First practical step.\nSecond practical step."


def _completion(content: object, finish_reason: str) -> object:
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content),
                finish_reason=finish_reason,
            )
        ],
        usage=SimpleNamespace(completion_tokens=1200),
    )


def test_gemini_provider_retries_once_after_length_finish_reason() -> None:
    completions = FakeChatCompletionsAPI(
        None,
        responses=[
            _completion("A partial answer", "length"),
            _completion("A complete practical answer.", "stop"),
        ],
    )
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    provider = GeminiLLMProvider(
        api_key=None,
        base_url=GEMINI_URL,
        model="test-gemini-model",
        max_output_tokens=1200,
        client=client,
    )

    result = asyncio.run(provider.generate(PROMPT))

    assert result == "A complete practical answer."
    assert [request["max_completion_tokens"] for request in completions.requests] == [
        1200,
        2400,
    ]


def test_gemini_provider_rejects_truncated_retry() -> None:
    completions = FakeChatCompletionsAPI(
        None,
        responses=[
            _completion("Partial one", "length"),
            _completion("Partial two", "length"),
        ],
    )
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    provider = GeminiLLMProvider(
        api_key=None,
        base_url=GEMINI_URL,
        model="test-gemini-model",
        client=client,
    )

    with pytest.raises(LLMIncompleteResponseError):
        asyncio.run(provider.generate(PROMPT))

    assert len(completions.requests) == 2


def test_gemini_provider_is_unavailable_without_api_key() -> None:
    provider = GeminiLLMProvider(
        api_key=None,
        base_url=GEMINI_URL,
        model="test-gemini-model",
    )

    assert not provider.is_configured
    with pytest.raises(LLMNotConfiguredError):
        asyncio.run(provider.generate(PROMPT))


@pytest.mark.parametrize(
    "provider_error",
    [
        openai.AuthenticationError(
            "invalid credential",
            response=_response(401),
            body=None,
        ),
        openai.RateLimitError(
            "rate limited",
            response=_response(429),
            body=None,
        ),
        openai.APITimeoutError(request=_request()),
        openai.APIConnectionError(request=_request()),
    ],
    ids=["authentication", "rate_limit", "timeout", "connection"],
)
def test_gemini_provider_maps_sdk_errors_safely(
    provider_error: BaseException,
    caplog: pytest.LogCaptureFixture,
) -> None:
    provider = GeminiLLMProvider(
        api_key=None,
        base_url=GEMINI_URL,
        model="test-gemini-model",
        client=FailingGeminiClient(provider_error),
    )

    with pytest.raises(LLMServiceUnavailableError):
        asyncio.run(provider.generate(PROMPT))

    assert "provider=gemini" in caplog.text
    assert "model=test-gemini-model" in caplog.text
    assert f"error_type={type(provider_error).__name__}" in caplog.text
    assert "Private user message" not in caplog.text
    assert "Stay in scope." not in caplog.text
    assert str(provider_error) not in caplog.text


def test_gemini_provider_exposes_rate_limit_as_retryable_domain_error() -> None:
    provider_error = openai.RateLimitError(
        "rate limited",
        response=_response(429),
        body=None,
    )
    provider = GeminiLLMProvider(
        api_key=None,
        base_url=GEMINI_URL,
        model="test-gemini-model",
        client=FailingGeminiClient(provider_error),
    )

    with pytest.raises(LLMRateLimitError):
        asyncio.run(provider.generate(PROMPT))


@pytest.mark.parametrize(
    "client",
    [
        FakeGeminiClient(None),
        FakeGeminiClient("   "),
        FakeGeminiClient("", include_choice=False),
    ],
    ids=["null_content", "blank_content", "no_choices"],
)
def test_gemini_provider_rejects_empty_responses(client: FakeGeminiClient) -> None:
    provider = GeminiLLMProvider(
        api_key=None,
        base_url=GEMINI_URL,
        model="test-gemini-model",
        client=client,
    )

    with pytest.raises(LLMInvalidResponseError):
        asyncio.run(provider.generate(PROMPT))


def test_gemini_provider_rejects_missing_content_field() -> None:
    completion = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(),
                finish_reason="stop",
            )
        ]
    )
    completions = FakeChatCompletionsAPI(None, responses=[completion])
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    provider = GeminiLLMProvider(
        api_key=None,
        base_url=GEMINI_URL,
        model="test-gemini-model",
        client=client,
    )

    with pytest.raises(LLMInvalidResponseError):
        asyncio.run(provider.generate(PROMPT))


def test_gemini_logs_only_safe_response_metadata(caplog) -> None:
    client = FakeGeminiClient("Safe answer")
    provider = GeminiLLMProvider(
        api_key=None,
        base_url=GEMINI_URL,
        model="test-gemini-model",
        client=client,
    )
    caplog.set_level("INFO", logger="app.infrastructure.llm.gemini_client")

    asyncio.run(provider.generate(PROMPT))

    assert "finish_reason=stop" in caplog.text
    assert "content_empty=False" in caplog.text
    assert "output_tokens=42" in caplog.text
    assert "Private user message" not in caplog.text
    assert "Safe answer" not in caplog.text
