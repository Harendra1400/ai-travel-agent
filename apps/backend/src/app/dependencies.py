"""Shared FastAPI dependency declarations."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.security import Principal, get_principal
from app.db.models import User
from app.db.models.enums import UserStatus
from app.db.session import get_session
from app.services.identity import get_or_create_user

SettingsDep = Annotated[Settings, Depends(get_settings)]
SessionDep = Annotated[AsyncSession, Depends(get_session)]
PrincipalDep = Annotated[Principal, Depends(get_principal)]


async def get_current_user(
    principal: PrincipalDep,
    session: SessionDep,
) -> User:
    """Resolve the authenticated principal to an application user."""
    user = await get_or_create_user(session, principal)
    if user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not active",
        )
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]
