"""Health endpoint."""

import asyncio
from collections.abc import Awaitable
from typing import Literal, cast

from fastapi import APIRouter, Response, status
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from qdrant_client import AsyncQdrantClient
from sqlalchemy import text

from app.core.metrics import http_metrics
from app.db.session import engine
from app.dependencies import SettingsDep
from app.infrastructure.redis import redis_client

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Public health response contract."""

    status: Literal["ok"]
    service: str
    version: str
    environment: str


class ReadinessResponse(BaseModel):
    """Dependency readiness result used by container orchestrators."""

    status: Literal["ready", "not_ready"]
    checks: dict[str, bool]


@router.get(
    "/metrics",
    response_class=PlainTextResponse,
    include_in_schema=False,
)
async def metrics() -> str:
    """Expose low-cardinality Prometheus metrics for this API process."""
    return http_metrics.render()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Check service health",
)
async def health(settings: SettingsDep) -> HealthResponse:
    """Report that the application process is available."""
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
    )


@router.get("/live", response_model=HealthResponse)
async def liveness(settings: SettingsDep) -> HealthResponse:
    """Report process liveness without touching external dependencies."""
    return await health(settings)


@router.get("/ready", response_model=ReadinessResponse)
async def readiness(
    response: Response,
    settings: SettingsDep,
) -> ReadinessResponse:
    """Verify that required infrastructure accepts requests."""

    async def database_ready() -> bool:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return True

    async def redis_ready() -> bool:
        ping = cast(Awaitable[bool], redis_client.ping())
        return bool(await ping)

    async def qdrant_ready() -> bool:
        api_key = (
            settings.qdrant_api_key.get_secret_value()
            if settings.qdrant_api_key
            else None
        )
        client = AsyncQdrantClient(url=settings.qdrant_url, api_key=api_key)
        try:
            await client.get_collections()
        finally:
            await client.close()
        return True

    probes: dict[str, Awaitable[bool]] = {
        "database": database_ready(),
        "redis": redis_ready(),
        "qdrant": qdrant_ready(),
    }
    results = await asyncio.gather(
        *(
            asyncio.wait_for(probe, settings.readiness_timeout_seconds)
            for probe in probes.values()
        ),
        return_exceptions=True,
    )
    checks = {
        name: result is True for name, result in zip(probes, results, strict=True)
    }
    ready = all(checks.values())
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadinessResponse(
        status="ready" if ready else "not_ready",
        checks=checks,
    )
