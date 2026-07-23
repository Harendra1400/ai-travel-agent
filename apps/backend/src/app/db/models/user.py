"""User account model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Index, String, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.models.enums import UserStatus, enum_values

if TYPE_CHECKING:
    from app.db.models.agent_run import AgentRun
    from app.db.models.booking import Booking
    from app.db.models.conversation import Conversation
    from app.db.models.memory import Memory
    from app.db.models.payment import Payment
    from app.db.models.preference import Preference
    from app.db.models.trip import Trip


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Application identity linked to an external OIDC subject."""

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint(
            "auth_issuer",
            "auth_subject",
            name="uq_users_auth_identity",
        ),
        CheckConstraint(
            "email = lower(email)",
            name="email_lowercase",
        ),
        Index("ix_users_status_created_at", "status", "created_at"),
    )

    auth_issuer: Mapped[str] = mapped_column(String(255), nullable=False)
    auth_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[UserStatus] = mapped_column(
        SAEnum(
            UserStatus,
            name="user_status",
            values_callable=enum_values,
        ),
        default=UserStatus.ACTIVE,
        server_default=UserStatus.ACTIVE.value,
        nullable=False,
    )
    last_login_at: Mapped[datetime | None]

    trips: Mapped[list[Trip]] = relationship(back_populates="user")
    conversations: Mapped[list[Conversation]] = relationship(back_populates="user")
    bookings: Mapped[list[Booking]] = relationship(back_populates="user")
    payments: Mapped[list[Payment]] = relationship(back_populates="user")
    agent_runs: Mapped[list[AgentRun]] = relationship(back_populates="user")
    preference: Mapped[Preference | None] = relationship(
        back_populates="user",
        uselist=False,
    )
    memories: Mapped[list[Memory]] = relationship(back_populates="user")
