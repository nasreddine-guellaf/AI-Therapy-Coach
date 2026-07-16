"""Deterministic first-line safety checks for conversation orchestration."""


class SafetyService:
    """Detect explicit crisis markers; this is not a diagnostic classifier."""

    _critical_markers = ("suicide", "me tuer", "danger immédiat")

    def requires_human_escalation(self, text: str) -> bool:
        """Return true for explicit markers requiring immediate human support."""
        normalized = text.casefold()
        return any(marker in normalized for marker in self._critical_markers)

    def crisis_message(self) -> str:
        """Return a fixed escalation message without invoking an LLM."""
        return (
            "Je ne peux pas gérer une urgence. Contactez immédiatement les services "
            "d'urgence locaux ou une personne de confiance. Ne restez pas seul(e)."
        )
