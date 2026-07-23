"""Metadata-level tests for the relational database design."""

from typing import cast

from sqlalchemy import Table, inspect

from app.db import Base
from app.db.models import AgentRun, Booking, User

EXPECTED_TABLES = {
    "agent_runs",
    "approvals",
    "audit_events",
    "bookings",
    "conversations",
    "itineraries",
    "itinerary_items",
    "memories",
    "messages",
    "outbox_events",
    "payments",
    "preferences",
    "provider_connections",
    "tool_calls",
    "trips",
    "travelers",
    "users",
}


def test_all_expected_tables_are_registered() -> None:
    """Every approved domain table is present in shared metadata."""
    assert set(Base.metadata.tables) == EXPECTED_TABLES


def test_primary_relationships_are_registered() -> None:
    """Critical aggregate relationships remain explicit and navigable."""
    assert {
        "trips",
        "conversations",
        "bookings",
        "payments",
        "agent_runs",
        "preference",
        "memories",
    } <= set(inspect(User).relationships.keys())
    assert {"messages", "tool_calls"} <= set(inspect(AgentRun).relationships.keys())
    assert "payments" in inspect(Booking).relationships


def test_constraints_and_indexes_have_names() -> None:
    """Migration operations can address every constraint and index by name."""
    for table in Base.metadata.sorted_tables:
        assert all(constraint.name for constraint in table.constraints)
        assert all(index.name for index in table.indexes)


def test_agent_run_has_database_enforced_idempotency() -> None:
    """Concurrent retries cannot create duplicate runs for one user."""
    table = cast(Table, AgentRun.__table__)
    constraint_names = {constraint.name for constraint in table.constraints}
    assert "uq_agent_runs_user_idempotency" in constraint_names
