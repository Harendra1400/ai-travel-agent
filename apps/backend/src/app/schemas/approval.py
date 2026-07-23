"""Human-in-the-loop approval API schemas."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.enums import ApprovalStatus, ToolRisk


class ApprovalRead(BaseModel):
    """Safe approval representation for a user decision."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    agent_run_id: UUID
    tool_call_id: UUID | None
    status: ApprovalStatus
    risk: ToolRisk
    version: int
    action_summary: str
    proposed_action: dict[str, object]
    expires_at: datetime
    created_at: datetime
    decided_at: datetime | None
    decision_reason: str | None


class ApprovalDecision(BaseModel):
    """Optimistic, auditable approval decision."""

    decision: Literal["approved", "rejected"]
    version: int = Field(gt=0)
    reason: str | None = Field(default=None, max_length=1000)
