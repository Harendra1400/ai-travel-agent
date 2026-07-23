"""Agent workflow run model."""

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
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin
from app.db.models.enums import AgentRunStatus, enum_values

if TYPE_CHECKING:
    from app.db.models.conversation import Conversation
    from app.db.models.message import Message
    from app.db.models.tool_call import ToolCall
    from app.db.models.trip import Trip
    from app.db.models.user import User


class AgentRun(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """A durable execution record for one LangGraph workflow."""

    __tablename__ = "agent_runs"
    __table_args__ = (
        CheckConstraint(
            "completed_at IS NULL OR started_at IS NULL "
            "OR completed_at >= started_at",
            name="valid_execution_window",
        ),
        UniqueConstraint(
            "user_id",
            "idempotency_key",
            name="uq_agent_runs_user_idempotency",
        ),
        CheckConstraint(
            "prompt_tokens >= 0 AND completion_tokens >= 0",
            name="nonnegative_tokens",
        ),
        CheckConstraint(
            "estimated_cost IS NULL OR estimated_cost >= 0",
            name="nonnegative_cost",
        ),
        Index(
            "ix_agent_runs_conversation_created",
            "conversation_id",
            "created_at",
        ),
        Index("ix_agent_runs_status_created", "status", "created_at"),
        Index("ix_agent_runs_trip_created", "trip_id", "created_at"),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    trip_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("trips.id", ondelete="SET NULL"),
    )
    parent_run_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="SET NULL"),
    )
    status: Mapped[AgentRunStatus] = mapped_column(
        SAEnum(
            AgentRunStatus,
            name="agent_run_status",
            values_callable=enum_values,
        ),
        default=AgentRunStatus.QUEUED,
        server_default=AgentRunStatus.QUEUED.value,
        nullable=False,
    )
    graph_name: Mapped[str] = mapped_column(String(120), nullable=False)
    graph_version: Mapped[str] = mapped_column(String(64), nullable=False)
    model_name: Mapped[str | None] = mapped_column(String(160))
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    input_payload: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )
    output_payload: Mapped[dict[str, object] | None] = mapped_column(JSONB)
    queued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(80))
    error_message: Mapped[str | None] = mapped_column(Text)
    prompt_tokens: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
    )
    completion_tokens: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
    )
    estimated_cost: Mapped[Decimal | None] = mapped_column(Numeric(14, 6))

    user: Mapped[User] = relationship(back_populates="agent_runs")
    conversation: Mapped[Conversation] = relationship(back_populates="agent_runs")
    trip: Mapped[Trip | None] = relationship(back_populates="agent_runs")
    parent: Mapped[AgentRun | None] = relationship(
        remote_side="AgentRun.id",
        back_populates="children",
    )
    children: Mapped[list[AgentRun]] = relationship(back_populates="parent")
    messages: Mapped[list[Message]] = relationship(back_populates="agent_run")
    tool_calls: Mapped[list[ToolCall]] = relationship(
        back_populates="agent_run",
        order_by="ToolCall.sequence_number",
    )
