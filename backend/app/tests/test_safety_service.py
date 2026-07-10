from app.domain.services.safety_service import SafetyService

def test_detects_explicit_critical_marker() -> None:
    assert SafetyService().requires_human_escalation("Je pense au suicide")

def test_neutral_message_is_not_escalated() -> None:
    assert not SafetyService().requires_human_escalation("Je souhaite parler de mon stress")
