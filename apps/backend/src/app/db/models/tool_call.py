"""Audited MCP tool-call model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
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
from app.db.models.enums import (
    ToolCallStatus,
    ToolRisk,
    enum_values,
)

if TYPE_CHECKING:
    from app.db.models.agent_run import AgentRun
    from app.db.models.booking import Booking


class ToolCall(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """A sanitized, auditable invocation of an MCP tool."""

    __tablename__ = "tool_calls"
    __table_args__ = (
        UniqueConstraint(
            "agent_run_id",
            "sequence_number",
            name="uq_tool_calls_run_sequence",
        ),
        UniqueConstraint(
            "idempotency_key",
            name="uq_tool_calls_idempotency",
        ),
        CheckConstraint("sequence_number > 0", name="positive_sequence"),
        CheckConstraint(
            "completed_at IS NULL OR started_at IS NULL "
            "OR completed_at >= started_at",
            name="valid_execution_window",
        ),
        Index(
            "ix_tool_calls_server_tool_created",
            "mcp_server",
            "tool_name",
            "created_at",
        ),
        Index("ix_tool_calls_status_created", "status", "created_at"),
    )

    agent_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    mcp_server: Mapped[str] = mapped_column(String(160), nullable=False)
    tool_name: Mapped[str] = mapped_column(String(160), nullable=False)
    risk: Mapped[ToolRisk] = mapped_column(
        SAEnum(
            ToolRisk,
            name="tool_risk",
            values_callable=enum_values,
        ),
        nullable=False,
    )
    status: Mapped[ToolCallStatus] = mapped_column(
        SAEnum(
            ToolCallStatus,
            name="tool_call_status",
            values_callable=enum_values,
        ),
        default=ToolCallStatus.PENDING,
        server_default=ToolCallStatus.PENDING.value,
        nullable=False,
    )
    request_payload: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
    )
    response_payload: Mapped[dict[str, object] | None] = mapped_column(JSONB)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(80))
    error_message: Mapped[str | None] = mapped_column(Text)

    agent_run: Mapped[AgentRun] = relationship(back_populates="tool_calls")
    bookings: Mapped[list[Booking]] = relationship(
        back_populates="source_tool_call",
    )
