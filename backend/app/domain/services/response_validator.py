"""Explainable rule-based validation for assistant responses.

This validator enforces product boundaries; it does not determine whether
medical advice is clinically correct and does not make the system a medical
device.
"""

from dataclasses import dataclass
from enum import StrEnum
import re


class ValidationViolation(StrEnum):
    EMPTY_RESPONSE = "empty_response"
    CLAIMS_PSYCHOLOGIST_IDENTITY = "claims_psychologist_identity"
    PROVIDES_MEDICAL_DIAGNOSIS = "provides_medical_diagnosis"
    PRESCRIBES_MEDICATION = "prescribes_medication"
    MISSING_PROFESSIONAL_HELP_REFERRAL = "missing_professional_help_referral"


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Auditable validation decision without retaining response content."""

    is_valid: bool
    violations: tuple[ValidationViolation, ...] = ()


class ResponseValidator:
    """Reject obvious boundary violations using explicit text patterns."""

    _PSYCHOLOGIST_CLAIMS = (
        r"\bi am (?:a |your )?psychologist\b",
        r"\bas your psychologist\b",
        r"\bje suis (?:un |une |votre )?psychologue\b",
        r"\ben tant que (?:votre )?psychologue\b",
    )
    _DIAGNOSIS_CLAIMS = (
        r"\bi diagnose you\b",
        r"\bmy diagnosis is\b",
        r"\byou (?:definitely )?(?:have|suffer from) "
        r"(?:depression|bipolar disorder|anxiety disorder|ptsd)\b",
        r"\bje vous diagnostique\b",
        r"\bmon diagnostic est\b",
        r"\bvous souffrez (?:de|d') (?:dépression|trouble bipolaire|trouble anxieux)\b",
    )
    _MEDICATION_PRESCRIPTIONS = (
        r"\bi prescribe\b",
        r"\bje (?:vous )?prescris\b",
        r"\b(?:take|start|stop|increase|decrease) \d+(?:[.,]\d+)?\s*(?:mg|milligrams?)\b",
        r"\b(?:prenez|commencez|arrêtez|augmentez|diminuez) "
        r"\d+(?:[.,]\d+)?\s*mg\b",
        r"\byou should (?:take|start|stop) "
        r"(?:prozac|fluoxetine|sertraline|xanax|alprazolam)\b",
    )
    _PROFESSIONAL_HELP_MARKERS = (
        "qualified professional",
        "healthcare professional",
        "mental health professional",
        "doctor",
        "clinician",
        "emergency services",
        "crisis line",
        "professionnel de santé",
        "professionnel qualifié",
        "médecin",
        "services d'urgence",
        "ligne de crise",
    )

    def assess(
        self, response: str, *, professional_help_required: bool = False
    ) -> ValidationResult:
        """Return named violations found in an assistant response."""
        normalized = " ".join(response.casefold().split())
        violations: list[ValidationViolation] = []

        if not normalized:
            violations.append(ValidationViolation.EMPTY_RESPONSE)
        if self._matches_any(normalized, self._PSYCHOLOGIST_CLAIMS):
            violations.append(ValidationViolation.CLAIMS_PSYCHOLOGIST_IDENTITY)
        if self._matches_any(normalized, self._DIAGNOSIS_CLAIMS):
            violations.append(ValidationViolation.PROVIDES_MEDICAL_DIAGNOSIS)
        if self._matches_any(normalized, self._MEDICATION_PRESCRIPTIONS):
            violations.append(ValidationViolation.PRESCRIBES_MEDICATION)
        if professional_help_required and not any(
            marker in normalized for marker in self._PROFESSIONAL_HELP_MARKERS
        ):
            violations.append(
                ValidationViolation.MISSING_PROFESSIONAL_HELP_REFERRAL
            )

        # TODO: add clinically reviewed multilingual policies, citation checks,
        # prompt-leakage detection, and a versioned secondary safety review.
        return ValidationResult(not violations, tuple(violations))

    def validate(
        self, response: str, *, professional_help_required: bool = False
    ) -> bool:
        """Return a compatibility-friendly boolean validation decision."""
        return self.assess(
            response, professional_help_required=professional_help_required
        ).is_valid

    @staticmethod
    def _matches_any(text: str, patterns: tuple[str, ...]) -> bool:
        return any(re.search(pattern, text) for pattern in patterns)
