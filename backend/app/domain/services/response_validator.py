class ResponseValidator:
    """Validates scope, attribution and unsafe medical claims."""

    def validate(self, response: str) -> bool:
        """Return whether an LLM response is minimally usable.

        TODO: replace this baseline with policy checks for medical claims,
        unsupported citations, crisis content, and prompt injection leakage.
        """
        # TODO: add policy-driven validation.
        return bool(response.strip())
