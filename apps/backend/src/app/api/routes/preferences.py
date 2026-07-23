"""Traveler preference endpoints."""

from fastapi import APIRouter, HTTPException

from app.dependencies import CurrentUserDep, SessionDep
from app.schemas.preference import PreferenceRead, PreferenceUpdate
from app.services.preferences import get_preferences, upsert_preferences

router = APIRouter(prefix="/v1/preferences", tags=["preferences"])


@router.get("", response_model=PreferenceRead)
async def get_user_preferences(
    session: SessionDep,
    user: CurrentUserDep,
) -> PreferenceRead:
    """Read the current user's planning defaults."""
    preference = await get_preferences(session, user)
    if preference is None:
        raise HTTPException(status_code=404, detail="Preferences not configured")
    return PreferenceRead.model_validate(preference)


@router.put("", response_model=PreferenceRead)
async def put_user_preferences(
    payload: PreferenceUpdate,
    session: SessionDep,
    user: CurrentUserDep,
) -> PreferenceRead:
    """Create or replace the current user's planning defaults."""
    preference = await upsert_preferences(session, user, payload)
    return PreferenceRead.model_validate(preference)
