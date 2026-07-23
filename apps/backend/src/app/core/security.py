"""OIDC bearer-token validation and authenticated principal extraction."""

from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated

import jwt
from anyio import to_thread
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings, get_settings

bearer_scheme = HTTPBearer(auto_error=False)


@lru_cache
def _jwks_client(url: str) -> jwt.PyJWKClient:
    """Reuse the JWKS cache and HTTP connection metadata across requests."""
    return jwt.PyJWKClient(url, cache_keys=True)


@dataclass(frozen=True, slots=True)
class Principal:
    """Verified caller identity supplied by the configured OIDC provider."""

    issuer: str
    subject: str
    email: str | None


async def get_principal(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Principal:
    """Validate a bearer token or supply the explicit local-development identity."""
    if settings.auth_disabled:
        return Principal(
            issuer="local-development",
            subject="local-user",
            email="local@example.com",
        )
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token required",
        )

    def decode_token() -> dict[str, object]:
        assert settings.auth_jwks_url is not None
        key = _jwks_client(settings.auth_jwks_url).get_signing_key_from_jwt(
            credentials.credentials
        )
        return jwt.decode(
            credentials.credentials,
            key.key,
            algorithms=["RS256", "ES256"],
            audience=settings.auth_audience,
            issuer=settings.auth_issuer,
        )

    try:
        claims = await to_thread.run_sync(decode_token)
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
        ) from exc

    subject = claims.get("sub")
    if not isinstance(subject, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token subject missing",
        )
    email_claim = claims.get("email")
    email = email_claim if isinstance(email_claim, str) else None
    return Principal(
        issuer=settings.auth_issuer or "",
        subject=subject,
        email=email,
    )
