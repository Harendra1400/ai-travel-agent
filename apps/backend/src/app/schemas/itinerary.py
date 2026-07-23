"""Versioned itinerary API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.db.models.enums import ItineraryItemKind, ItineraryStatus


class ItineraryItemRead(BaseModel):
    """One structured segment in an itinerary version."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    position: int
    kind: ItineraryItemKind
    title: str
    starts_at: datetime | None
    ends_at: datetime | None
    location: dict[str, object]
    details: dict[str, object]


class ItineraryRead(BaseModel):
    """Versioned itinerary proposal."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    trip_id: UUID
    agent_run_id: UUID | None
    version: int
    status: ItineraryStatus
    title: str
    summary: str | None
    accepted_at: datetime | None
    created_at: datetime
    items: list[ItineraryItemRead]
