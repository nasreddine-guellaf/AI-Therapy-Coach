"""Prompt construction rules for the conversation use case."""

from collections.abc import Sequence


class PromptBuilder:
    """Build a bounded prompt from policy, memory, evidence, and user input."""

    def build(
        self,
        user_message: str,
        memory_context: Sequence[str],
        retrieved_context: Sequence[str] = (),
    ) -> str:
        """Create a provider-neutral prompt with clearly separated context."""
        memory_section = "\n".join(f"- {item}" for item in memory_context) or "- None"
        evidence_section = (
            "\n".join(f"- {item}" for item in retrieved_context) or "- None"
        )
        return (
            "You are a non-medical coaching assistant. Do not diagnose, prescribe, "
            "or claim to replace a healthcare professional.\n\n"
            f"Recent conversation memory:\n{memory_section}\n\n"
            f"Retrieved knowledge:\n{evidence_section}\n\n"
            f"User message:\n{user_message}"
        )
