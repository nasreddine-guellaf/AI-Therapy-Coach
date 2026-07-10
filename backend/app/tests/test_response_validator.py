from app.domain.services.response_validator import ResponseValidator

def test_rejects_empty_response() -> None:
    assert not ResponseValidator().validate("   ")
