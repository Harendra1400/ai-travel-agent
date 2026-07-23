"""Governed long-term memory API schemas."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.enums import MemoryKind


class MemoryCreate(BaseModel):
    """Explicit memory a user permits the agent to retain."""

    kind: MemoryKind
    content: str = Field(min_length=1, max_length=10_000)
    trip_id: UUID | None = None
    conversation_id: UUID | None = None
    confidence: Decimal = Field(default=Decimal("1"), ge=0, le=1)
    importance: Decimal = Field(default=Decimal("0.5"), ge=0, le=1)
    expires_at: datetime | None = None


class MemoryRead(BaseModel):
    """Source-of-truth memory metadata returned to its owner."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    kind: MemoryKind
    content: str
    trip_id: UUID | None
    conversation_id: UUID | None
    confidence: Decimal
    importance: Decimal
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime
