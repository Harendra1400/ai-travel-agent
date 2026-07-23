"""Conversation message model."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin
from app.db.models.enums import MessageRole, enum_values

if TYPE_CHECKING:
    from app.db.models.agent_run import AgentRun
    from app.db.models.conversation import Conversation
    from app.db.models.memory import Memory


class Message(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """An immutable ordered message within a conversation."""

    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint(
            "conversation_id",
            "sequence_number",
            name="uq_messages_conversation_sequence",
        ),
        UniqueConstraint(
            "conversation_id",
            "idempotency_key",
            name="uq_messages_conversation_idempotency",
        ),
        CheckConstraint("sequence_number > 0", name="positive_sequence"),
        CheckConstraint(
            "token_count IS NULL OR token_count >= 0",
            name="nonnegative_token_count",
        ),
        CheckConstraint(
            "content IS NOT NULL OR content_json IS NOT NULL",
            name="content_present",
        ),
        Index("ix_messages_conversation_created", "conversation_id", "created_at"),
        Index("ix_messages_agent_run", "agent_run_id"),
    )

    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_run_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="SET NULL"),
    )
    parent_message_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("messages.id", ondelete="SET NULL"),
    )
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[MessageRole] = mapped_column(
        SAEnum(
            MessageRole,
            name="message_role",
            values_callable=enum_values,
        ),
        nullable=False,
    )
    content: Mapped[str | None] = mapped_column(Text)
    content_json: Mapped[dict[str, object] | None] = mapped_column(JSONB)
    token_count: Mapped[int | None]
    idempotency_key: Mapped[str | None] = mapped_column(String(128))

    conversation: Mapped[Conversation] = relationship(back_populates="messages")
    agent_run: Mapped[AgentRun | None] = relationship(back_populates="messages")
    parent: Mapped[Message | None] = relationship(
        remote_side="Message.id",
        back_populates="children",
    )
    children: Mapped[list[Message]] = relationship(back_populates="parent")
    derived_memories: Mapped[list[Memory]] = relationship(
        back_populates="source_message",
    )
