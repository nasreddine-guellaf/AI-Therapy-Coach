from app.domain.services.prompt_builder import PromptBuilder

def test_prompt_contains_user_message() -> None:
    assert "bonjour" in PromptBuilder().build("bonjour", [])
