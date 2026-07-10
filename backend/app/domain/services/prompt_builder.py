class PromptBuilder:
    """Builds bounded prompts from policy, history and retrieved evidence."""
    def build(self, user_message: str, context: list[str]) -> str:
        return f"Contexte:\n{' '.join(context)}\nUtilisateur: {user_message}"
