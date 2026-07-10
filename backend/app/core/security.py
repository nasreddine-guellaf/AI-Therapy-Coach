"""Security primitives placeholder (authentication, authorization, rate limiting)."""

def redact_secret(value: str | None) -> str:
    return "***" if value else ""
