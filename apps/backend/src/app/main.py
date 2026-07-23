"""FastAPI application entry point and resource lifecycle."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.routes.agent_runs import router as agent_runs_router
from app.api.routes.approvals import router as approvals_router
from app.api.routes.conversations import router as conversations_router
from app.api.routes.health import router as health_router
from app.api.routes.itineraries import router as itineraries_router
from app.api.routes.memories import router as memories_router
from app.api.routes.preferences import router as preferences_router
from app.api.routes.trips import router as trips_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.observability import RequestContextMiddleware
from app.db.session import close_database
from app.infrastructure.redis import close_redis

settings = get_settings()
configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Close shared external clients during graceful shutdown."""
    yield
    await close_redis()
    await close_database()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url=None if settings.environment == "production" else "/docs",
    redoc_url=None if settings.environment == "production" else "/redoc",
)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
)
app.include_router(health_router)
app.include_router(trips_router)
app.include_router(conversations_router)
app.include_router(agent_runs_router)
app.include_router(approvals_router)
app.include_router(memories_router)
app.include_router(itineraries_router)
app.include_router(preferences_router)
