"""Conversation and message API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.enums import ConversationStatus, MessageRole


class ConversationCreate(BaseModel):
    """Fields accepted when starting a conversation."""

    trip_id: UUID | None = None
    title: str | None = Field(default=None, max_length=160)


class ConversationRead(BaseModel):
    """Conversation summary."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    trip_id: UUID | None
    title: str | None
    status: ConversationStatus
    last_message_at: datetime | None
    created_at: datetime
    updated_at: datetime


class MessageCreate(BaseModel):
    """User-authored message input."""

    content: str = Field(min_length=1, max_length=20_000)
    idempotency_key: str = Field(min_length=8, max_length=128)


class MessageRead(BaseModel):
    """Ordered transcript message."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sequence_number: int
    role: MessageRole
    content: str | None
    created_at: datetime
