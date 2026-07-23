"""Authenticated user provisioning."""

from hashlib import sha256

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import Principal
from app.db.models import User


async def get_or_create_user(
    session: AsyncSession,
    principal: Principal,
) -> User:
    """Resolve an OIDC identity and provision its application user once."""
    result = await session.execute(
        select(User).where(
            User.auth_issuer == principal.issuer,
            User.auth_subject == principal.subject,
        )
    )
    if user := result.scalar_one_or_none():
        return user

    identity_hash = sha256(
        f"{principal.issuer}:{principal.subject}".encode()
    ).hexdigest()[:24]
    fallback_email = f"{identity_hash}@invalid.local"
    user = User(
        auth_issuer=principal.issuer,
        auth_subject=principal.subject,
        email=(principal.email or fallback_email).lower(),
    )
    session.add(user)
    await session.flush()
    return user
