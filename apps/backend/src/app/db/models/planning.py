"""Traveler and versioned itinerary models."""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.models.enums import (
    ItineraryItemKind,
    ItineraryStatus,
    enum_values,
)

if TYPE_CHECKING:
    from app.db.models.agent_run import AgentRun
    from app.db.models.tool_call import ToolCall
    from app.db.models.trip import Trip
    from app.db.models.user import User


class Traveler(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A traveler participating in a trip without storing raw identity documents."""

    __tablename__ = "travelers"
    __table_args__ = (
        CheckConstraint(
            "date_of_birth IS NULL OR date_of_birth <= CURRENT_DATE",
            name="birth_date_not_future",
        ),
        Index("ix_travelers_trip_created", "trip_id", "created_at"),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    trip_id: Mapped[UUID] = mapped_column(
        ForeignKey("trips.id", ondelete="CASCADE"),
        nullable=False,
    )
    given_name: Mapped[str] = mapped_column(String(120), nullable=False)
    family_name: Mapped[str] = mapped_column(String(120), nullable=False)
    date_of_birth: Mapped[date | None]
    loyalty_programs: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )

    user: Mapped[User] = relationship()
    trip: Mapped[Trip] = relationship()


class Itinerary(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An immutable-by-version itinerary proposal for a trip."""

    __tablename__ = "itineraries"
    __table_args__ = (
        CheckConstraint("version > 0", name="positive_version"),
        Index(
            "uq_itineraries_trip_version",
            "trip_id",
            "version",
            unique=True,
        ),
        Index("ix_itineraries_trip_status", "trip_id", "status"),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    trip_id: Mapped[UUID] = mapped_column(
        ForeignKey("trips.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_run_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="SET NULL"),
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[ItineraryStatus] = mapped_column(
        SAEnum(
            ItineraryStatus,
            name="itinerary_status",
            values_callable=enum_values,
        ),
        default=ItineraryStatus.DRAFT,
        server_default=ItineraryStatus.DRAFT.value,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    summary: Mapped[str | None] = mapped_column(String(2000))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship()
    trip: Mapped[Trip] = relationship()
    agent_run: Mapped[AgentRun | None] = relationship()
    items: Mapped[list[ItineraryItem]] = relationship(
        back_populates="itinerary",
        order_by="ItineraryItem.position",
    )


class ItineraryItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One ordered, structured segment of an itinerary version."""

    __tablename__ = "itinerary_items"
    __table_args__ = (
        CheckConstraint("position > 0", name="positive_position"),
        Index(
            "uq_itinerary_items_itinerary_position",
            "itinerary_id",
            "position",
            unique=True,
        ),
        Index("ix_itinerary_items_time", "itinerary_id", "starts_at"),
    )

    itinerary_id: Mapped[UUID] = mapped_column(
        ForeignKey("itineraries.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_tool_call_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("tool_calls.id", ondelete="SET NULL"),
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[ItineraryItemKind] = mapped_column(
        SAEnum(
            ItineraryItemKind,
            name="itinerary_item_kind",
            values_callable=enum_values,
        ),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    location: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )
    details: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )

    itinerary: Mapped[Itinerary] = relationship(back_populates="items")
    source_tool_call: Mapped[ToolCall | None] = relationship()
