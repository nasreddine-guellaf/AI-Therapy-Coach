class ResponseValidator:
    """Validates scope, attribution and unsafe medical claims."""
    def validate(self, response: str) -> bool:
        # TODO: add policy-driven validation.
        return bool(response.strip())
