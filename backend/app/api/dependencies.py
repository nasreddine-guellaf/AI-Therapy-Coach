"""FastAPI dependency providers and composition placeholders."""
from app.domain.services.conversation_manager import ConversationManager

def get_conversation_manager() -> ConversationManager:
    # TODO: inject concrete repositories/providers at the composition root.
    return ConversationManager()
