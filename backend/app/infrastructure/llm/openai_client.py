from app.domain.interfaces.llm_provider import LLMProvider

class OpenAILLMProvider(LLMProvider):
    """OpenAI adapter placeholder; no SDK call is made."""
    async def generate(self, prompt: str) -> str:
        raise NotImplementedError("TODO: configure an OpenAI client")
