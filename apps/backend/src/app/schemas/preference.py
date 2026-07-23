"""Traveler preference API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.enums import CabinClass


class PreferenceUpdate(BaseModel):
    """Mutable planning defaults for the authenticated traveler."""

    home_airport: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    default_currency: str = Field(default="USD", pattern=r"^[A-Z]{3}$")
    locale: str = Field(default="en-US", max_length=35)
    timezone: str = Field(default="UTC", max_length=64)
    cabin_class: CabinClass = CabinClass.ECONOMY
    max_layovers: int | None = Field(default=None, ge=0, le=10)
    prefers_direct: bool = False
    dietary_requirements: list[str] = Field(default_factory=list, max_length=50)
    accessibility_requirements: list[str] = Field(
        default_factory=list,
        max_length=50,
    )


class PreferenceRead(PreferenceUpdate):
    """Persisted traveler preferences."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime
