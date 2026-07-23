"""Versioned itinerary persistence and acceptance."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.state import PlannedItineraryItem
from app.db.models import AgentRun, Itinerary, ItineraryItem, Trip, User
from app.db.models.enums import (
    ItineraryItemKind,
    ItineraryStatus,
    TripStatus,
)


async def persist_itinerary(
    session: AsyncSession,
    run: AgentRun,
    *,
    plan: str,
    items: list[PlannedItineraryItem],
) -> Itinerary | None:
    """Create one immutable itinerary version for a completed planning run."""
    if run.trip_id is None:
        return None
    existing = await session.scalar(
        select(Itinerary).where(Itinerary.agent_run_id == run.id)
    )
    if existing is not None:
        return existing

    trip = await session.scalar(
        select(Trip).where(Trip.id == run.trip_id).with_for_update()
    )
    if trip is None:
        return None
    latest_version = await session.scalar(
        select(func.max(Itinerary.version)).where(Itinerary.trip_id == trip.id)
    )
    await session.execute(
        update(Itinerary)
        .where(
            Itinerary.trip_id == trip.id,
            Itinerary.status == ItineraryStatus.PROPOSED,
        )
        .values(status=ItineraryStatus.SUPERSEDED)
    )
    itinerary = Itinerary(
        user_id=run.user_id,
        trip_id=trip.id,
        agent_run_id=run.id,
        version=(latest_version or 0) + 1,
        status=ItineraryStatus.PROPOSED,
        title=trip.title,
        summary=plan[:2000],
    )
    session.add(itinerary)
    await session.flush()
    for position, item in enumerate(items, start=1):
        session.add(
            ItineraryItem(
                itinerary_id=itinerary.id,
                position=position,
                kind=ItineraryItemKind(item["kind"]),
                title=item["title"],
                starts_at=item["starts_at"],
                ends_at=item["ends_at"],
                location=item["location"],
                details=item["details"],
            )
        )
    trip.status = TripStatus.PLANNING
    return itinerary


async def list_itineraries(
    session: AsyncSession,
    user: User,
    trip_id: UUID,
) -> list[Itinerary] | None:
    """List itinerary versions after enforcing trip ownership."""
    owned = await session.scalar(
        select(Trip.id).where(Trip.id == trip_id, Trip.user_id == user.id)
    )
    if owned is None:
        return None
    result = await session.scalars(
        select(Itinerary)
        .where(Itinerary.trip_id == trip_id, Itinerary.user_id == user.id)
        .options(selectinload(Itinerary.items))
        .order_by(Itinerary.version.desc())
    )
    return list(result)


async def accept_itinerary(
    session: AsyncSession,
    user: User,
    itinerary_id: UUID,
) -> Itinerary | None:
    """Accept one proposal and supersede every other unaccepted version."""
    itinerary = await session.scalar(
        select(Itinerary)
        .where(
            Itinerary.id == itinerary_id,
            Itinerary.user_id == user.id,
        )
        .options(selectinload(Itinerary.items))
        .with_for_update()
    )
    if itinerary is None:
        return None
    if itinerary.status != ItineraryStatus.PROPOSED:
        raise ValueError("Only a proposed itinerary can be accepted")
    await session.execute(
        update(Itinerary)
        .where(
            Itinerary.trip_id == itinerary.trip_id,
            Itinerary.id != itinerary.id,
            Itinerary.status.in_((ItineraryStatus.DRAFT, ItineraryStatus.PROPOSED)),
        )
        .values(status=ItineraryStatus.SUPERSEDED)
    )
    itinerary.status = ItineraryStatus.ACCEPTED
    itinerary.accepted_at = datetime.now(UTC)
    return itinerary
