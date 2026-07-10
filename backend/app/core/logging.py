import logging

def configure_logging() -> None:
    """Configure application logging without exposing user or secret data."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
