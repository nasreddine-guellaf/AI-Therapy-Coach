from app.domain.services.prompt_builder import PromptBuilder


def test_prompt_contains_user_message() -> None:
    prompt = PromptBuilder().build("bonjour", [])
    assert "bonjour" in prompt.input
    assert "Never diagnose" in prompt.instructions
