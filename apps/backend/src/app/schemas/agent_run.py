"""Agent-run API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.enums import AgentRunStatus


class AgentRunCreate(BaseModel):
    """Request a durable planning run from a conversation message."""

    conversation_id: UUID
    trip_id: UUID | None = None
    request: str = Field(min_length=1, max_length=20_000)
    idempotency_key: str = Field(min_length=8, max_length=128)


class AgentRunRead(BaseModel):
    """Agent-run status and eventual result."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    trip_id: UUID | None
    status: AgentRunStatus
    model_name: str | None
    output_payload: dict[str, object] | None
    error_code: str | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
