"""Trip application service."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Trip, User
from app.schemas.trip import TripCreate


async def create_trip(
    session: AsyncSession,
    user: User,
    payload: TripCreate,
) -> Trip:
    """Create one user-owned trip."""
    trip = Trip(user_id=user.id, **payload.model_dump())
    session.add(trip)
    await session.flush()
    await session.refresh(trip)
    return trip


async def list_trips(session: AsyncSession, user: User) -> list[Trip]:
    """List the authenticated user's trips newest first."""
    result = await session.scalars(
        select(Trip).where(Trip.user_id == user.id).order_by(Trip.created_at.desc())
    )
    return list(result)


async def get_trip(
    session: AsyncSession,
    user: User,
    trip_id: UUID,
) -> Trip | None:
    """Load a trip only when owned by the authenticated user."""
    trip: Trip | None = await session.scalar(
        select(Trip).where(Trip.id == trip_id, Trip.user_id == user.id)
    )
    return trip
