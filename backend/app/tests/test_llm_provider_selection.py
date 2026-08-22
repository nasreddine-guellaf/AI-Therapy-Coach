"""Tests for provider selection at the FastAPI composition boundary."""

from app.api.dependencies import build_llm_provider
from app.core.config import settings
from app.infrastructure.llm.gemini_client import GeminiLLMProvider
from app.infrastructure.llm.openai_client import OpenAILLMProvider
from app.infrastructure.llm.openrouter_client import OpenRouterLLMProvider


def test_openai_selection_logs_safe_configuration(monkeypatch, caplog) -> None:
    monkeypatch.setattr(settings, "llm_provider", "openai")
    monkeypatch.setattr(settings, "openai_api_key", "another-secret-test-key")
    caplog.set_level("INFO", logger="app.api.dependencies")

    assert isinstance(build_llm_provider(), OpenAILLMProvider)
    assert "provider=openai" in caplog.text
    assert "api_key_present=True" in caplog.text
    assert f"model={settings.openai_model}" in caplog.text
    assert "another-secret-test-key" not in caplog.text


def test_openrouter_selection_logs_safe_configuration(monkeypatch, caplog) -> None:
    monkeypatch.setattr(settings, "llm_provider", "openrouter")
    monkeypatch.setattr(settings, "openrouter_api_key", "super-secret-test-key")
    caplog.set_level("INFO", logger="app.api.dependencies")

    provider = build_llm_provider()

    assert isinstance(provider, OpenRouterLLMProvider)
    assert provider.model == settings.openrouter_model
    assert provider.is_configured
    assert "provider=openrouter" in caplog.text
    assert "api_key_present=True" in caplog.text
    assert f"model={settings.openrouter_model}" in caplog.text
    assert "super-secret-test-key" not in caplog.text


def test_gemini_selection_logs_safe_configuration(monkeypatch, caplog) -> None:
    monkeypatch.setattr(settings, "llm_provider", "gemini")
    monkeypatch.setattr(settings, "gemini_api_key", "gemini-secret-test-key")
    caplog.set_level("INFO", logger="app.api.dependencies")

    provider = build_llm_provider()

    assert isinstance(provider, GeminiLLMProvider)
    assert provider.model == settings.gemini_model
    assert provider.base_url == settings.gemini_base_url.rstrip("/")
    assert provider.max_output_tokens == settings.gemini_max_output_tokens
    assert provider.is_configured
    assert "provider=gemini" in caplog.text
    assert "api_key_present=True" in caplog.text
    assert f"model={settings.gemini_model}" in caplog.text
    assert "gemini-secret-test-key" not in caplog.text


def test_gemini_selection_without_key_stays_unconfigured(
    monkeypatch,
    caplog,
) -> None:
    monkeypatch.setattr(settings, "llm_provider", "gemini")
    monkeypatch.setattr(settings, "gemini_api_key", None)
    caplog.set_level("INFO", logger="app.api.dependencies")

    provider = build_llm_provider()

    assert isinstance(provider, GeminiLLMProvider)
    assert not provider.is_configured
    assert "provider=gemini" in caplog.text
    assert "api_key_present=False" in caplog.text
