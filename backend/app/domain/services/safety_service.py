class SafetyService:
    """Deterministic first-line guardrail; not a diagnostic classifier."""
    _critical_markers = ("suicide", "me tuer", "danger immédiat")

    def requires_human_escalation(self, text: str) -> bool:
        normalized = text.casefold()
        return any(marker in normalized for marker in self._critical_markers)

    def crisis_message(self) -> str:
        return ("Je ne peux pas gérer une urgence. Contactez immédiatement les services "
                "d'urgence locaux ou une personne de confiance. Ne restez pas seul(e).")
