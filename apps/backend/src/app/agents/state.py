"""Typed state passed between LangGraph nodes."""

from datetime import datetime
from typing import Literal, TypedDict


class RequestedTool(TypedDict):
    """One allow-listed MCP tool request proposed by the planner."""

    server: str
    tool: str
    arguments: dict[str, object]


class PlannedItineraryItem(TypedDict):
    """Structured itinerary segment emitted by the planner."""

    kind: Literal[
        "flight",
        "lodging",
        "rail",
        "transfer",
        "activity",
        "meal",
        "note",
    ]
    title: str
    starts_at: datetime | None
    ends_at: datetime | None
    location: dict[str, object]
    details: dict[str, object]


class TravelGraphState(TypedDict, total=False):
    """Minimal auditable state for one travel-planning run."""

    request: str
    user_id: str
    trip_id: str | None
    context: list[str]
    plan: str
    itinerary_items: list[PlannedItineraryItem]
    requested_tools: list[RequestedTool]
    validation_errors: list[str]
