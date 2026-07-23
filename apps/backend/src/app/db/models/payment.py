"""Payment ledger model."""

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

from app.db.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin
from app.db.models.enums import (
    PaymentKind,
    PaymentStatus,
    enum_values,
)

if TYPE_CHECKING:
    from app.db.models.booking import Booking
    from app.db.models.user import User


class Payment(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """An immutable payment-provider operation for a booking."""

    __tablename__ = "payments"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "provider_payment_id",
            name="uq_payments_provider_reference",
        ),
        UniqueConstraint(
            "idempotency_key",
            name="uq_payments_idempotency",
        ),
        CheckConstraint("amount > 0", name="positive_amount"),
        CheckConstraint(
            "currency ~ '^[A-Z]{3}$'",
            name="currency_iso_format",
        ),
        Index("ix_payments_booking_created", "booking_id", "created_at"),
        Index("ix_payments_user_status_created", "user_id", "status", "created_at"),
    )

    booking_id: Mapped[UUID] = mapped_column(
        ForeignKey("bookings.id", ondelete="RESTRICT"),
        nullable=False,
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(String(120), nullable=False)
    provider_payment_id: Mapped[str | None] = mapped_column(String(160))
    kind: Mapped[PaymentKind] = mapped_column(
        SAEnum(
            PaymentKind,
            name="payment_kind",
            values_callable=enum_values,
        ),
        nullable=False,
    )
    status: Mapped[PaymentStatus] = mapped_column(
        SAEnum(
            PaymentStatus,
            name="payment_status",
            values_callable=enum_values,
        ),
        default=PaymentStatus.PENDING,
        server_default=PaymentStatus.PENDING.value,
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    provider_metadata: Mapped[dict[str, object]] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
        nullable=False,
    )

    booking: Mapped[Booking] = relationship(back_populates="payments")
    user: Mapped[User] = relationship(back_populates="payments")
