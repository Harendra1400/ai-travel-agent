"""Trip HTTP routes."""

from fastapi import APIRouter

from app.dependencies import CurrentUserDep, SessionDep
from app.schemas.trip import TripCreate, TripRead
from app.services.trips import create_trip, list_trips

router = APIRouter(prefix="/v1/trips", tags=["trips"])


@router.post("", response_model=TripRead, status_code=201)
async def post_trip(
    payload: TripCreate,
    session: SessionDep,
    user: CurrentUserDep,
) -> TripRead:
    """Create a travel plan for the authenticated user."""
    trip = await create_trip(session, user, payload)
    return TripRead.model_validate(trip)


@router.get("", response_model=list[TripRead])
async def get_trips(
    session: SessionDep,
    user: CurrentUserDep,
) -> list[TripRead]:
    """List travel plans owned by the authenticated user."""
    return [TripRead.model_validate(trip) for trip in await list_trips(session, user)]
