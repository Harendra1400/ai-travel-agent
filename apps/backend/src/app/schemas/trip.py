"""Trip API schemas."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.db.models.enums import TripStatus


class TripCreate(BaseModel):
    """Fields accepted when creating a travel plan."""

    title: str = Field(min_length=1, max_length=160)
    destination_summary: str = Field(min_length=1, max_length=2000)
    origin_code: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    start_date: date | None = None
    end_date: date | None = None
    party_size: int = Field(default=1, gt=0, le=100)
    budget_amount: Decimal | None = Field(default=None, ge=0)
    currency: str = Field(default="USD", pattern=r"^[A-Z]{3}$")

    @model_validator(mode="after")
    def validate_date_range(self) -> "TripCreate":
        """Reject inverted trip dates before reaching PostgreSQL."""
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.end_date < self.start_date
        ):
            raise ValueError("end_date must be on or after start_date")
        return self


class TripRead(BaseModel):
    """Stable trip representation returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    destination_summary: str
    origin_code: str | None
    start_date: date | None
    end_date: date | None
    party_size: int
    budget_amount: Decimal | None
    currency: str
    status: TripStatus
    created_at: datetime
    updated_at: datetime
