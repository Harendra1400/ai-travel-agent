"""Conversation and message HTTP routes."""

from fastapi import APIRouter, HTTPException, status

from app.dependencies import CurrentUserDep, SessionDep
from app.schemas.conversation import (
    ConversationCreate,
    ConversationRead,
    MessageCreate,
    MessageRead,
)
from app.services.conversations import add_user_message, create_conversation

router = APIRouter(prefix="/v1/conversations", tags=["conversations"])


@router.post("", response_model=ConversationRead, status_code=201)
async def post_conversation(
    payload: ConversationCreate,
    session: SessionDep,
    user: CurrentUserDep,
) -> ConversationRead:
    """Start a conversation."""
    conversation = await create_conversation(session, user, payload)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    return ConversationRead.model_validate(conversation)


@router.post(
    "/{conversation_id}/messages",
    response_model=MessageRead,
    status_code=201,
)
async def post_message(
    conversation_id: str,
    payload: MessageCreate,
    session: SessionDep,
    user: CurrentUserDep,
) -> MessageRead:
    """Append an idempotent user message."""
    from uuid import UUID

    message = await add_user_message(
        session,
        user,
        UUID(conversation_id),
        payload,
    )
    if message is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    return MessageRead.model_validate(message)
