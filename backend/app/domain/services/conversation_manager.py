from app.schemas.conversation_schema import ConversationRequest, ConversationResponse
from app.domain.services.safety_service import SafetyService

class ConversationManager:
    """Coordinates safety, memory, retrieval, prompting, generation and validation."""
    def __init__(self, safety: SafetyService | None = None) -> None:
        self.safety = safety or SafetyService()

    async def handle(self, request: ConversationRequest) -> ConversationResponse:
        # TODO: orchestrate injected ports (compatible with LangChain/LangGraph later).
        if self.safety.requires_human_escalation(request.message):
            return ConversationResponse(message=self.safety.crisis_message(), status="escalation_required")
        return ConversationResponse(message="Service de conversation à connecter.", status="pending")
