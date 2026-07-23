"""Travel booking model."""

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
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.models.enums import (
    BookingStatus,
    BookingType,
    enum_values,
)

if TYPE_CHECKING:
    from app.db.models.payment import Payment
    from app.db.models.tool_call import ToolCall
    from app.db.models.trip import Trip
    from app.db.models.user import User


class Booking(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A provider booking associated with a trip."""

    __tablename__ = "bookings"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "provider_booking_id",
            name="uq_bookings_provider_reference",
        ),
        CheckConstraint("amount >= 0", name="nonnegative_amount"),
        CheckConstraint(
            "currency ~ '^[A-Z]{3}$'",
            name="currency_iso_format",
        ),
        CheckConstraint(
            "end_at IS NULL OR start_at IS NULL OR end_at >= start_at",
            name="valid_service_window",
        ),
        Index("ix_bookings_user_status_created", "user_id", "status", "created_at"),
        Index("ix_bookings_trip_status", "trip_id", "status"),
        Index("ix_bookings_start", "start_at"),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    trip_id: Mapped[UUID] = mapped_column(
        ForeignKey("trips.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_tool_call_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("tool_calls.id", ondelete="SET NULL"),
    )
    provider: Mapped[str] = mapped_column(String(120), nullable=False)
    provider_booking_id: Mapped[str | None] = mapped_column(String(160))
    booking_type: Mapped[BookingType] = mapped_column(
        SAEnum(
            BookingType,
            name="booking_type",
            values_callable=enum_values,
        ),
        nullable=False,
    )
    status: Mapped[BookingStatus] = mapped_column(
        SAEnum(
            BookingStatus,
            name="booking_status",
            values_callable=enum_values,
        ),
        default=BookingStatus.PENDING,
        server_default=BookingStatus.PENDING.value,
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    booked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancellation_deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    details: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="bookings")
    trip: Mapped[Trip] = relationship(back_populates="bookings")
    source_tool_call: Mapped[ToolCall | None] = relationship(
        back_populates="bookings",
    )
    payments: Mapped[list[Payment]] = relationship(back_populates="booking")
