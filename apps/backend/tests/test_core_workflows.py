"""Unit tests for configuration, policy, security, and planner safeguards."""

import logging
from datetime import date

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import HttpUrl, ValidationError

from app.agents.planner import validate_plan
from app.core.config import MCPServerSettings, MCPToolSettings, Settings
from app.core.logging import JSONFormatter, request_id_context
from app.core.metrics import HTTPMetrics
from app.core.security import get_principal
from app.mcp_gateway.policy import ToolNotAllowedError, resolve_tool_policy
from app.schemas.trip import TripCreate


def test_production_configuration_rejects_unsafe_defaults() -> None:
    """Production cannot start with authentication or host controls disabled."""
    with pytest.raises(ValidationError, match="Authentication cannot be disabled"):
        Settings(environment="production")
    with pytest.raises(ValidationError, match="Wildcard trusted hosts"):
        Settings(
            environment="production",
            auth_disabled=False,
            auth_issuer="https://id.example.com",
            auth_audience="travel",
            auth_jwks_url="https://id.example.com/jwks",
            allowed_hosts=["*"],
        )


def test_configuration_rejects_unknown_mcp_server() -> None:
    """Allow-listed tools must reference a configured server."""
    with pytest.raises(ValidationError, match="unknown servers"):
        Settings(
            mcp_tools=[
                MCPToolSettings(
                    server="missing",
                    tool="search",
                    risk="read",
                )
            ]
        )


def test_tool_policy_is_deny_by_default_and_classifies_side_effects() -> None:
    """Only exact configured tool names receive a policy."""
    settings = Settings(
        mcp_servers={
            "travel": MCPServerSettings(
                url=HttpUrl("https://mcp.example.com"),
                granted_scopes=["booking:write"],
            )
        },
        mcp_tools=[
            MCPToolSettings(server="travel", tool="search", risk="read"),
            MCPToolSettings(
                server="travel",
                tool="book",
                risk="financial",
                required_scopes=["booking:write"],
            ),
        ],
    )
    assert not resolve_tool_policy(settings, "travel", "search").requires_human_approval
    booking = resolve_tool_policy(settings, "travel", "book")
    assert booking.requires_human_approval
    assert booking.required_scopes == frozenset({"booking:write"})
    with pytest.raises(ToolNotAllowedError):
        resolve_tool_policy(settings, "travel", "invented")


async def test_planner_validation_rejects_empty_and_transactional_claims() -> None:
    """Deterministic validation blocks unsupported claims."""
    assert await validate_plan({"plan": ""}) == {
        "validation_errors": ["Planner returned an empty result"]
    }
    result = await validate_plan({"plan": "Your booking confirmed today"})
    assert result["validation_errors"] == [
        "Plan contains an unsupported transactional claim"
    ]
    assert await validate_plan({"plan": "A proposed three-day plan"}) == {
        "validation_errors": []
    }


async def test_local_principal_and_missing_bearer_behavior() -> None:
    """Local auth is explicit, while enabled auth requires a bearer token."""
    local = await get_principal(None, Settings(environment="test"))
    assert local.subject == "local-user"
    secure = Settings(
        environment="test",
        auth_disabled=False,
        auth_issuer="https://id.example.com",
        auth_audience="travel",
        auth_jwks_url="https://id.example.com/jwks",
    )
    with pytest.raises(HTTPException) as error:
        await get_principal(None, secure)
    assert error.value.status_code == 401


async def test_invalid_bearer_is_not_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    """JWT verification failures produce a generic unauthorized response."""
    secure = Settings(
        environment="test",
        auth_disabled=False,
        auth_issuer="https://id.example.com",
        auth_audience="travel",
        auth_jwks_url="https://id.example.com/jwks",
    )

    class BrokenJWKS:
        def get_signing_key_from_jwt(self, _: str) -> None:
            raise jwt.PyJWTError("do not disclose parser details")

    monkeypatch.setattr("app.core.security._jwks_client", lambda _: BrokenJWKS())
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="bad")
    with pytest.raises(HTTPException) as error:
        await get_principal(credentials, secure)
    assert error.value.status_code == 401


def test_structured_logging_and_trip_date_validation() -> None:
    """Logs carry correlation IDs and request validation catches bad ranges."""
    token = request_id_context.set("request-123")
    try:
        output = JSONFormatter().format(
            logging.LogRecord(
                "test",
                logging.INFO,
                __file__,
                1,
                "completed",
                (),
                None,
            )
        )
    finally:
        request_id_context.reset(token)
    assert '"request_id":"request-123"' in output
    with pytest.raises(ValidationError, match="end_date"):
        TripCreate(
            title="Bad dates",
            destination_summary="Rome",
            start_date=date(2027, 5, 10),
            end_date=date(2027, 5, 1),
        )


def test_metrics_registry_tracks_low_cardinality_totals() -> None:
    """Metrics aggregate only method/status labels and duration totals."""
    metrics = HTTPMetrics()
    metrics.observe("GET", 200, 0.25)
    metrics.observe("GET", 200, 0.75)
    output = metrics.render()
    assert 'method="GET",status="200"} 2' in output
    assert 'method="GET",status="200"} 1.000000' in output
