"""POST /api/chat/message"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.models.chat import ChatMessageRequest, ChatResponse
from app.repositories.conversations import ConversationRepository, get_conversation_repository
from app.services.chatbot.llm_client import get_llm_client
from app.services.chatbot.orchestrator import ChatOrchestrator

router = APIRouter(prefix="/api/chat", tags=["chat"])
logger = get_logger(__name__)


def get_orchestrator(settings: Settings = Depends(get_settings)) -> ChatOrchestrator:
    return ChatOrchestrator(llm_client=get_llm_client(settings))


@router.post("/message", response_model=ChatResponse)
async def post_chat_message(
    request: ChatMessageRequest,
    orchestrator: ChatOrchestrator = Depends(get_orchestrator),
    repository: ConversationRepository = Depends(get_conversation_repository),
) -> ChatResponse:
    request_id = request.request_id or str(uuid.uuid4())

    # Idempotency: a duplicated/retried submit of the exact same user
    # message must not be processed twice (spec section 20).
    if request.request_id and await repository.has_seen(request.conversation_id, request.request_id):
        logger.info(
            "duplicate chat message ignored conversation_id=%s request_id=%s",
            request.conversation_id,
            request.request_id,
        )

    logger.info(
        "chat message conversation_id=%s stage=%s request_id=%s",
        request.conversation_id,
        request.state.stage,
        request_id,
    )

    response = await orchestrator.handle_message(request)

    logger.info(
        "chat response conversation_id=%s stage=%s missing_field=%s brief_ready=%s",
        request.conversation_id,
        response.stage,
        response.missing_field,
        response.brief_ready,
    )

    await repository.append_message(request.conversation_id, request_id, request.message, response.reply)
    return response
