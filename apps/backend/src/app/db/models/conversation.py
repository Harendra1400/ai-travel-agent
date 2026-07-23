"""Conversation model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.models.enums import ConversationStatus, enum_values

if TYPE_CHECKING:
    from app.db.models.agent_run import AgentRun
    from app.db.models.memory import Memory
    from app.db.models.message import Message
    from app.db.models.trip import Trip
    from app.db.models.user import User


class Conversation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A persistent user interaction thread, optionally attached to a trip."""

    __tablename__ = "conversations"
    __table_args__ = (
        Index("ix_conversations_user_updated", "user_id", "updated_at"),
        Index("ix_conversations_trip_updated", "trip_id", "updated_at"),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    trip_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("trips.id", ondelete="SET NULL"),
    )
    title: Mapped[str | None] = mapped_column(String(160))
    status: Mapped[ConversationStatus] = mapped_column(
        SAEnum(
            ConversationStatus,
            name="conversation_status",
            values_callable=enum_values,
        ),
        default=ConversationStatus.ACTIVE,
        server_default=ConversationStatus.ACTIVE.value,
        nullable=False,
    )
    last_message_at: Mapped[datetime | None]

    user: Mapped[User] = relationship(back_populates="conversations")
    trip: Mapped[Trip | None] = relationship(back_populates="conversations")
    messages: Mapped[list[Message]] = relationship(
        back_populates="conversation",
        order_by="Message.sequence_number",
    )
    agent_runs: Mapped[list[AgentRun]] = relationship(
        back_populates="conversation",
    )
    memories: Mapped[list[Memory]] = relationship(back_populates="conversation")
