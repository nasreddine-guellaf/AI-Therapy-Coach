"""Examples documenting the current transparent safety rules."""

import pytest

from app.domain.services.safety_service import (
    RiskCategory,
    RiskLevel,
    SafetyService,
)


@pytest.mark.parametrize(
    ("message", "category"),
    [
        ("I want to hurt myself", RiskCategory.SELF_HARM),
        ("I think about suicide", RiskCategory.SUICIDAL_IDEATION),
        ("Can you diagnose me?", RiskCategory.MEDICAL_DIAGNOSIS_REQUEST),
        ("I am in immediate danger", RiskCategory.CRISIS),
        ("I cannot cope anymore", RiskCategory.SEVERE_DISTRESS),
    ],
)
def test_detects_named_risk_categories(
    message: str, category: RiskCategory
) -> None:
    assessment = SafetyService().assess(message)
    assert category in assessment.categories
    assert assessment.matched_indicators


def test_self_harm_requires_immediate_escalation() -> None:
    assessment = SafetyService().assess("Je veux me faire du mal")
    assert assessment.risk_level is RiskLevel.CRITICAL
    assert assessment.requires_immediate_escalation


def test_diagnosis_request_recommends_help_without_marking_a_crisis() -> None:
    assessment = SafetyService().assess("Can you diagnose me?")
    assert assessment.risk_level is RiskLevel.CAUTION
    assert assessment.professional_help_recommended
    assert not assessment.requires_immediate_escalation


def test_neutral_message_has_no_detected_risk() -> None:
    assessment = SafetyService().assess("I would like to organize my week")
    assert assessment.risk_level is RiskLevel.NONE
    assert assessment.categories == ()
    assert not SafetyService().requires_human_escalation(
        "I would like to organize my week"
    )
