"""Versioned itinerary query and acceptance endpoints."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.dependencies import CurrentUserDep, SessionDep
from app.schemas.itinerary import ItineraryRead
from app.services.itineraries import accept_itinerary, list_itineraries

router = APIRouter(tags=["itineraries"])


@router.get("/v1/trips/{trip_id}/itineraries", response_model=list[ItineraryRead])
async def get_trip_itineraries(
    trip_id: UUID,
    session: SessionDep,
    user: CurrentUserDep,
) -> list[ItineraryRead]:
    """List all itinerary versions for an owned trip."""
    itineraries = await list_itineraries(session, user, trip_id)
    if itineraries is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    return [ItineraryRead.model_validate(item) for item in itineraries]


@router.post(
    "/v1/itineraries/{itinerary_id}/accept",
    response_model=ItineraryRead,
)
async def post_accept_itinerary(
    itinerary_id: UUID,
    session: SessionDep,
    user: CurrentUserDep,
) -> ItineraryRead:
    """Accept an owned proposed itinerary."""
    try:
        itinerary = await accept_itinerary(session, user, itinerary_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    if itinerary is None:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    return ItineraryRead.model_validate(itinerary)
