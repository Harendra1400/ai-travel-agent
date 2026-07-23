"""Conversation and ordered-message application service."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Conversation, Message, Trip, User
from app.db.models.enums import MessageRole
from app.schemas.conversation import ConversationCreate, MessageCreate


async def create_conversation(
    session: AsyncSession,
    user: User,
    payload: ConversationCreate,
) -> Conversation | None:
    """Start a conversation owned by the authenticated user."""
    if payload.trip_id is not None:
        trip = await session.scalar(
            select(Trip.id).where(
                Trip.id == payload.trip_id,
                Trip.user_id == user.id,
            )
        )
        if trip is None:
            return None
    conversation = Conversation(user_id=user.id, **payload.model_dump())
    session.add(conversation)
    await session.flush()
    await session.refresh(conversation)
    return conversation


async def get_conversation(
    session: AsyncSession,
    user: User,
    conversation_id: UUID,
    *,
    for_update: bool = False,
) -> Conversation | None:
    """Load a conversation with ownership enforcement."""
    statement = select(Conversation).where(
        Conversation.id == conversation_id,
        Conversation.user_id == user.id,
    )
    if for_update:
        statement = statement.with_for_update()
    conversation: Conversation | None = await session.scalar(statement)
    return conversation


async def add_user_message(
    session: AsyncSession,
    user: User,
    conversation_id: UUID,
    payload: MessageCreate,
) -> Message | None:
    """Append an idempotent message while serializing sequence allocation."""
    conversation = await get_conversation(
        session,
        user,
        conversation_id,
        for_update=True,
    )
    if conversation is None:
        return None

    existing = await session.scalar(
        select(Message).where(
            Message.conversation_id == conversation_id,
            Message.idempotency_key == payload.idempotency_key,
        )
    )
    if existing is not None:
        return existing

    latest = await session.scalar(
        select(func.max(Message.sequence_number)).where(
            Message.conversation_id == conversation_id
        )
    )
    message = Message(
        conversation_id=conversation_id,
        sequence_number=(latest or 0) + 1,
        role=MessageRole.USER,
        content=payload.content,
        idempotency_key=payload.idempotency_key,
    )
    conversation.last_message_at = datetime.now(UTC)
    session.add(message)
    await session.flush()
    return message
