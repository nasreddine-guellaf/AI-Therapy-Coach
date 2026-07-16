"""Examples documenting response boundary validation."""

import pytest

from app.domain.services.response_validator import (
    ResponseValidator,
    ValidationViolation,
)


@pytest.mark.parametrize(
    ("response", "violation"),
    [
        (
            "I am your psychologist and I know what is best.",
            ValidationViolation.CLAIMS_PSYCHOLOGIST_IDENTITY,
        ),
        (
            "You definitely have depression.",
            ValidationViolation.PROVIDES_MEDICAL_DIAGNOSIS,
        ),
        (
            "You should take Prozac.",
            ValidationViolation.PRESCRIBES_MEDICATION,
        ),
    ],
)
def test_rejects_explicit_boundary_violations(
    response: str, violation: ValidationViolation
) -> None:
    result = ResponseValidator().assess(response)
    assert not result.is_valid
    assert violation in result.violations


def test_requires_professional_referral_when_flagged() -> None:
    validator = ResponseValidator()
    missing = validator.assess(
        "Let us try a breathing exercise.", professional_help_required=True
    )
    present = validator.assess(
        "Please contact a qualified professional for appropriate support.",
        professional_help_required=True,
    )

    assert ValidationViolation.MISSING_PROFESSIONAL_HELP_REFERRAL in missing.violations
    assert present.is_valid


def test_allows_transparent_scope_disclaimer() -> None:
    response = (
        "I am not a psychologist and cannot diagnose or prescribe medication. "
        "A healthcare professional can provide an appropriate assessment."
    )
    assert ResponseValidator().validate(response, professional_help_required=True)


def test_rejects_empty_response() -> None:
    result = ResponseValidator().assess("   ")
    assert ValidationViolation.EMPTY_RESPONSE in result.violations
