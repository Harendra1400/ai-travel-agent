"""Trip aggregate model."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, Numeric, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.models.enums import TripStatus, enum_values

if TYPE_CHECKING:
    from app.db.models.agent_run import AgentRun
    from app.db.models.booking import Booking
    from app.db.models.conversation import Conversation
    from app.db.models.memory import Memory
    from app.db.models.user import User


class Trip(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A user-owned travel plan and its constraints."""

    __tablename__ = "trips"
    __table_args__ = (
        CheckConstraint(
            "end_date IS NULL OR start_date IS NULL OR end_date >= start_date",
            name="valid_date_range",
        ),
        CheckConstraint("party_size > 0", name="positive_party_size"),
        CheckConstraint(
            "budget_amount IS NULL OR budget_amount >= 0",
            name="nonnegative_budget",
        ),
        CheckConstraint(
            "currency ~ '^[A-Z]{3}$'",
            name="currency_iso_format",
        ),
        CheckConstraint(
            "origin_code IS NULL OR origin_code ~ '^[A-Z]{3}$'",
            name="origin_iata_format",
        ),
        Index("ix_trips_user_status_start", "user_id", "status", "start_date"),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    origin_code: Mapped[str | None] = mapped_column(String(3))
    destination_summary: Mapped[str] = mapped_column(Text, nullable=False)
    start_date: Mapped[date | None]
    end_date: Mapped[date | None]
    status: Mapped[TripStatus] = mapped_column(
        SAEnum(
            TripStatus,
            name="trip_status",
            values_callable=enum_values,
        ),
        default=TripStatus.DRAFT,
        server_default=TripStatus.DRAFT.value,
        nullable=False,
    )
    party_size: Mapped[int] = mapped_column(default=1, server_default="1")
    budget_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    currency: Mapped[str] = mapped_column(
        String(3),
        default="USD",
        server_default="USD",
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="trips")
    conversations: Mapped[list[Conversation]] = relationship(back_populates="trip")
    bookings: Mapped[list[Booking]] = relationship(back_populates="trip")
    agent_runs: Mapped[list[AgentRun]] = relationship(back_populates="trip")
    memories: Mapped[list[Memory]] = relationship(back_populates="trip")
