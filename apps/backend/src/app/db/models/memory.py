"""Long-term agent memory model."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.models.enums import MemoryKind, enum_values

if TYPE_CHECKING:
    from app.db.models.conversation import Conversation
    from app.db.models.message import Message
    from app.db.models.trip import Trip
    from app.db.models.user import User


class Memory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A governed memory record whose UUID can also key a Qdrant point."""

    __tablename__ = "memories"
    __table_args__ = (
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="confidence_unit_interval",
        ),
        CheckConstraint(
            "importance >= 0 AND importance <= 1",
            name="importance_unit_interval",
        ),
        Index("ix_memories_user_kind_created", "user_id", "kind", "created_at"),
        Index("ix_memories_trip_kind", "trip_id", "kind"),
        Index("ix_memories_conversation", "conversation_id"),
        Index(
            "ix_memories_expires_at",
            "expires_at",
            postgresql_where=text("expires_at IS NOT NULL"),
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    trip_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("trips.id", ondelete="SET NULL"),
    )
    conversation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("conversations.id", ondelete="SET NULL"),
    )
    source_message_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("messages.id", ondelete="SET NULL"),
    )
    kind: Mapped[MemoryKind] = mapped_column(
        SAEnum(
            MemoryKind,
            name="memory_kind",
            values_callable=enum_values,
        ),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding_model: Mapped[str | None] = mapped_column(String(160))
    confidence: Mapped[Decimal] = mapped_column(
        Numeric(4, 3),
        default=1,
        server_default="1",
        nullable=False,
    )
    importance: Mapped[Decimal] = mapped_column(
        Numeric(4, 3),
        default=0.5,
        server_default="0.5",
        nullable=False,
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_accessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="memories")
    trip: Mapped[Trip | None] = relationship(back_populates="memories")
    conversation: Mapped[Conversation | None] = relationship(back_populates="memories")
    source_message: Mapped[Message | None] = relationship(
        back_populates="derived_memories"
    )
