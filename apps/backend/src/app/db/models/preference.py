"""User travel-preference model."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, String, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.models.enums import CabinClass, enum_values

if TYPE_CHECKING:
    from app.db.models.user import User


class Preference(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One optional, structured travel-preference profile per user."""

    __tablename__ = "preferences"
    __table_args__ = (
        CheckConstraint(
            "home_airport IS NULL OR home_airport ~ '^[A-Z]{3}$'",
            name="home_airport_iata_format",
        ),
        CheckConstraint(
            "default_currency ~ '^[A-Z]{3}$'",
            name="currency_iso_format",
        ),
        CheckConstraint(
            "max_layovers IS NULL OR max_layovers >= 0",
            name="nonnegative_max_layovers",
        ),
        CheckConstraint(
            "jsonb_typeof(dietary_requirements) = 'array'",
            name="dietary_requirements_array",
        ),
        CheckConstraint(
            "jsonb_typeof(accessibility_requirements) = 'array'",
            name="accessibility_requirements_array",
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    home_airport: Mapped[str | None] = mapped_column(String(3))
    default_currency: Mapped[str] = mapped_column(
        String(3),
        default="USD",
        server_default="USD",
        nullable=False,
    )
    locale: Mapped[str] = mapped_column(
        String(35),
        default="en-US",
        server_default="en-US",
        nullable=False,
    )
    timezone: Mapped[str] = mapped_column(
        String(64),
        default="UTC",
        server_default="UTC",
        nullable=False,
    )
    cabin_class: Mapped[CabinClass] = mapped_column(
        SAEnum(
            CabinClass,
            name="cabin_class",
            values_callable=enum_values,
        ),
        default=CabinClass.ECONOMY,
        server_default=CabinClass.ECONOMY.value,
        nullable=False,
    )
    max_layovers: Mapped[int | None] = mapped_column(Integer)
    prefers_direct: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )
    dietary_requirements: Mapped[list[str]] = mapped_column(
        JSONB,
        default=list,
        server_default=text("'[]'::jsonb"),
        nullable=False,
    )
    accessibility_requirements: Mapped[list[str]] = mapped_column(
        JSONB,
        default=list,
        server_default=text("'[]'::jsonb"),
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="preference")
