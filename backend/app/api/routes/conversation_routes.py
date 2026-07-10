from fastapi import APIRouter, Depends, status
from app.api.dependencies import get_conversation_manager
from app.domain.services.conversation_manager import ConversationManager
from app.schemas.conversation_schema import ConversationRequest, ConversationResponse

router = APIRouter(prefix="/conversation", tags=["conversation"])

@router.post("/message", response_model=ConversationResponse, status_code=status.HTTP_202_ACCEPTED)
async def send_message(request: ConversationRequest, manager: ConversationManager = Depends(get_conversation_manager)) -> ConversationResponse:
    return await manager.handle(request)
