"""Provider connection, audit, and transactional outbox models."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.models.enums import (
    OutboxStatus,
    ProviderConnectionStatus,
    enum_values,
)

if TYPE_CHECKING:
    from app.db.models.user import User


class ProviderConnection(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Reference to provider credentials held by an external secret vault."""

    __tablename__ = "provider_connections"
    __table_args__ = (
        Index(
            "uq_provider_connections_user_provider",
            "user_id",
            "provider",
            unique=True,
        ),
        Index("ix_provider_connections_status_expiry", "status", "expires_at"),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[ProviderConnectionStatus] = mapped_column(
        SAEnum(
            ProviderConnectionStatus,
            name="provider_connection_status",
            values_callable=enum_values,
        ),
        default=ProviderConnectionStatus.ACTIVE,
        server_default=ProviderConnectionStatus.ACTIVE.value,
        nullable=False,
    )
    vault_secret_ref: Mapped[str] = mapped_column(String(500), nullable=False)
    scopes: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship()


class AuditEvent(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Append-only security and business audit event."""

    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_events_user_created", "user_id", "created_at"),
        Index(
            "ix_audit_events_resource_created",
            "resource_type",
            "resource_id",
            "created_at",
        ),
    )

    user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    actor_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(160), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(120), nullable=False)
    resource_id: Mapped[UUID | None]
    outcome: Mapped[str] = mapped_column(String(80), nullable=False)
    event_metadata: Mapped[dict[str, object]] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
        nullable=False,
    )


class OutboxEvent(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Transactional event awaiting reliable external publication."""

    __tablename__ = "outbox_events"
    __table_args__ = (
        Index("ix_outbox_events_dispatch", "status", "available_at", "created_at"),
        Index("ix_outbox_events_aggregate", "aggregate_type", "aggregate_id"),
    )

    aggregate_type: Mapped[str] = mapped_column(String(120), nullable=False)
    aggregate_id: Mapped[UUID] = mapped_column(nullable=False)
    event_type: Mapped[str] = mapped_column(String(160), nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    status: Mapped[OutboxStatus] = mapped_column(
        SAEnum(
            OutboxStatus,
            name="outbox_status",
            values_callable=enum_values,
        ),
        default=OutboxStatus.PENDING,
        server_default=OutboxStatus.PENDING.value,
        nullable=False,
    )
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
    )
    last_error: Mapped[str | None] = mapped_column(Text)
