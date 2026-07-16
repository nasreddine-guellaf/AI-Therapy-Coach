"""Transparent rule-based user-message safety screening.

This module supports a non-medical coaching product. It is not a medical device,
does not assess clinical risk, and must not be presented as a substitute for a
qualified professional or local emergency service.
"""

from dataclasses import dataclass
from enum import StrEnum


class RiskCategory(StrEnum):
    """Auditable categories detected by the initial rules."""

    SELF_HARM = "self_harm"
    SUICIDAL_IDEATION = "suicidal_ideation"
    MEDICAL_DIAGNOSIS_REQUEST = "medical_diagnosis_request"
    CRISIS = "crisis"
    SEVERE_DISTRESS = "severe_distress"


class RiskLevel(StrEnum):
    NONE = "none"
    CAUTION = "caution"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class SafetyAssessment:
    """Explainable output containing categories and matched public rules."""

    risk_level: RiskLevel
    categories: tuple[RiskCategory, ...] = ()
    matched_indicators: tuple[str, ...] = ()

    @property
    def requires_immediate_escalation(self) -> bool:
        return self.risk_level is RiskLevel.CRITICAL

    @property
    def professional_help_recommended(self) -> bool:
        return self.risk_level is not RiskLevel.NONE


class SafetyService:
    """Detect explicit phrases using deterministic, reviewable rules.

    The rules intentionally favor transparency over pretending to understand
    clinical context. They can miss risk and can produce false positives.
    """

    _RULES: dict[RiskCategory, tuple[str, ...]] = {
        RiskCategory.SELF_HARM: (
            "harm myself",
            "hurt myself",
            "cut myself",
            "me faire du mal",
            "m'automutiler",
        ),
        RiskCategory.SUICIDAL_IDEATION: (
            "suicide",
            "kill myself",
            "end my life",
            "want to die",
            "me tuer",
            "mettre fin à mes jours",
            "envie de mourir",
        ),
        RiskCategory.MEDICAL_DIAGNOSIS_REQUEST: (
            "diagnose me",
            "do i have depression",
            "am i depressed",
            "am i bipolar",
            "what disorder do i have",
            "quel est mon diagnostic",
            "est-ce que je suis dépressif",
            "diagnostic médical",
        ),
        RiskCategory.CRISIS: (
            "immediate danger",
            "emergency situation",
            "cannot stay safe",
            "can't stay safe",
            "danger immédiat",
            "situation d'urgence",
            "je ne suis pas en sécurité",
        ),
        RiskCategory.SEVERE_DISTRESS: (
            "cannot cope",
            "can't cope",
            "panic attack",
            "feel hopeless",
            "je n'en peux plus",
            "crise de panique",
            "je suis désespéré",
            "je suis désespérée",
        ),
    }

    _CRITICAL_CATEGORIES = {
        RiskCategory.SELF_HARM,
        RiskCategory.SUICIDAL_IDEATION,
        RiskCategory.CRISIS,
    }

    def assess(self, text: str) -> SafetyAssessment:
        """Return all categories matched by explicit case-insensitive phrases."""
        normalized = " ".join(text.casefold().split())
        categories: list[RiskCategory] = []
        indicators: list[str] = []

        for category, phrases in self._RULES.items():
            matches = [phrase for phrase in phrases if phrase in normalized]
            if matches:
                categories.append(category)
                indicators.extend(matches)

        category_set = set(categories)
        if category_set & self._CRITICAL_CATEGORIES:
            level = RiskLevel.CRITICAL
        elif RiskCategory.SEVERE_DISTRESS in category_set:
            level = RiskLevel.HIGH
        elif RiskCategory.MEDICAL_DIAGNOSIS_REQUEST in category_set:
            level = RiskLevel.CAUTION
        else:
            level = RiskLevel.NONE

        # TODO: add multilingual, clinically reviewed rules and negation/context
        # handling. A future safety model may supplement these rules, but must
        # expose versioned decisions and remain under human governance.
        return SafetyAssessment(level, tuple(categories), tuple(indicators))

    def requires_human_escalation(self, text: str) -> bool:
        """Preserve the simple API used by conversation orchestration."""
        return self.assess(text).requires_immediate_escalation

    def crisis_message(self) -> str:
        """Return fixed guidance without generating or diagnosing anything."""
        return (
            "Je ne peux pas gérer une urgence. Contactez immédiatement les services "
            "d'urgence locaux ou une personne de confiance. Ne restez pas seul(e)."
        )
