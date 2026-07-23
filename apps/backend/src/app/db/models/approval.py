"""Human approval records for high-risk agent actions."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.models.enums import ApprovalStatus, ToolRisk, enum_values

if TYPE_CHECKING:
    from app.db.models.agent_run import AgentRun
    from app.db.models.tool_call import ToolCall
    from app.db.models.user import User


class Approval(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Versioned, expiring user decision for one proposed agent action."""

    __tablename__ = "approvals"
    __table_args__ = (
        CheckConstraint("version > 0", name="positive_version"),
        CheckConstraint(
            "decided_at IS NULL OR decided_at >= created_at",
            name="decision_after_creation",
        ),
        Index("ix_approvals_user_status_created", "user_id", "status", "created_at"),
        Index("ix_approvals_run_status", "agent_run_id", "status"),
        Index("ix_approvals_expires", "status", "expires_at"),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    agent_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    tool_call_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("tool_calls.id", ondelete="SET NULL"),
    )
    status: Mapped[ApprovalStatus] = mapped_column(
        SAEnum(
            ApprovalStatus,
            name="approval_status",
            values_callable=enum_values,
        ),
        default=ApprovalStatus.PENDING,
        server_default=ApprovalStatus.PENDING.value,
        nullable=False,
    )
    risk: Mapped[ToolRisk] = mapped_column(
        SAEnum(ToolRisk, name="tool_risk", values_callable=enum_values),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    action_summary: Mapped[str] = mapped_column(String(500), nullable=False)
    proposed_action: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decision_reason: Mapped[str | None] = mapped_column(String(1000))

    user: Mapped[User] = relationship()
    agent_run: Mapped[AgentRun] = relationship()
    tool_call: Mapped[ToolCall | None] = relationship()
