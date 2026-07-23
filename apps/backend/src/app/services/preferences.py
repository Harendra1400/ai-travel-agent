"""Authenticated traveler preference service."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Preference, User
from app.schemas.preference import PreferenceUpdate


async def get_preferences(
    session: AsyncSession,
    user: User,
) -> Preference | None:
    """Load the current user's single preference record."""
    preference: Preference | None = await session.scalar(
        select(Preference).where(Preference.user_id == user.id)
    )
    return preference


async def upsert_preferences(
    session: AsyncSession,
    user: User,
    payload: PreferenceUpdate,
) -> Preference:
    """Create or replace the current user's planning defaults."""
    preference = await get_preferences(session, user)
    values = payload.model_dump()
    if preference is None:
        preference = Preference(user_id=user.id, **values)
        session.add(preference)
    else:
        for key, value in values.items():
            setattr(preference, key, value)
    await session.flush()
    return preference
