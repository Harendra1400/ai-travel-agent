"""Tests for the health endpoint."""

from httpx import ASGITransport, AsyncClient

from app.core.config import Settings, get_settings
from app.main import app


async def test_health_returns_service_status_and_request_id() -> None:
    """The health endpoint exposes a stable, correlated operational contract."""
    app.dependency_overrides[get_settings] = lambda: Settings(environment="test")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.get("/health")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["x-request-id"]
    assert response.json() == {
        "status": "ok",
        "service": "AI Travel Agent API",
        "version": "0.1.0",
        "environment": "test",
    }
