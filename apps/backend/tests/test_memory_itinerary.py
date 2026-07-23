"""Tests for governed memory and versioned itinerary persistence."""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.db.models import AgentRun, Memory, Trip, User
from app.db.models.enums import AgentRunStatus, ItineraryStatus, MemoryKind
from app.schemas.memory import MemoryCreate
from app.services.itineraries import accept_itinerary, persist_itinerary
from app.services.memories import (
    create_memory,
    index_memory,
    retrieve_relevant_memories,
)


def _session() -> MagicMock:
    session = MagicMock()
    session.scalar = AsyncMock()
    session.scalars = AsyncMock()
    session.get = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.delete = AsyncMock()
    session.execute = AsyncMock()
    return session


async def test_memory_creation_stages_vector_index() -> None:
    """PostgreSQL memory and outbox event are staged in one transaction."""
    session = _session()
    user = User(
        id=uuid4(),
        auth_issuer="test",
        auth_subject="user",
        email="user@example.com",
    )
    memory = await create_memory(
        session,
        user,
        MemoryCreate(kind=MemoryKind.PREFERENCE, content="Aisle seats"),
        Settings(),
    )
    assert memory is not None
    assert memory.user_id == user.id
    assert len(memory.content_hash) == 64
    assert session.add.call_count == 2


async def test_memory_index_and_retrieval_are_tenant_filtered(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Embedding jobs index an owned payload and retrieval returns active content."""
    session = _session()
    memory = Memory(
        id=uuid4(),
        user_id=uuid4(),
        kind=MemoryKind.FACT,
        content="Vegetarian traveler",
        content_hash="a" * 64,
        embedding_model="embedding",
    )
    session.get.return_value = memory
    embeddings = AsyncMock(
        return_value=SimpleNamespace(data=[SimpleNamespace(embedding=[0.1, 0.2])])
    )
    openai = MagicMock()
    openai.return_value.embeddings.create = embeddings
    store = MagicMock()
    store.return_value.upsert = AsyncMock()
    store.return_value.search = AsyncMock(
        return_value=[{"content": "Vegetarian traveler", "expires_at": None}]
    )
    store.return_value.close = AsyncMock()
    monkeypatch.setattr("app.services.memories.AsyncOpenAI", openai)
    monkeypatch.setattr("app.services.memories.MemoryVectorStore", store)
    settings = Settings(
        openai_api_key=SecretStr("test"),
        embedding_dimensions=2,
    )
    await index_memory(session, memory.id, settings)
    store.return_value.upsert.assert_awaited_once()
    results = await retrieve_relevant_memories(
        user_id=memory.user_id,
        query="food",
        settings=settings,
    )
    assert results == ["Vegetarian traveler"]
    store.return_value.search.assert_awaited_once()


async def test_itinerary_version_is_created_and_can_be_accepted() -> None:
    """Completed plans become structured, accept-once itinerary versions."""
    session = _session()
    trip = Trip(
        id=uuid4(),
        user_id=uuid4(),
        title="Japan",
        destination_summary="Tokyo",
    )
    run = AgentRun(
        id=uuid4(),
        user_id=trip.user_id,
        conversation_id=uuid4(),
        trip_id=trip.id,
        status=AgentRunStatus.RUNNING,
        graph_name="travel-planner",
        graph_version="1",
        idempotency_key="run-key",
        input_payload={},
        queued_at=datetime.now(UTC),
    )
    session.scalar.side_effect = [None, trip, 2]
    itinerary = await persist_itinerary(
        session,
        run,
        plan="A three-day itinerary",
        items=[
            {
                "kind": "activity",
                "title": "Museum",
                "starts_at": None,
                "ends_at": None,
                "location": {},
                "details": {},
            }
        ],
    )
    assert itinerary is not None
    assert itinerary.version == 3
    assert itinerary.status.value == "proposed"
    assert trip.status.value == "planning"

    itinerary.items = []
    session.scalar.side_effect = None
    session.scalar.return_value = itinerary
    accepted = await accept_itinerary(
        session,
        User(
            id=trip.user_id,
            auth_issuer="test",
            auth_subject="user",
            email="user@example.com",
        ),
        itinerary.id,
    )
    assert accepted is itinerary
    assert itinerary.status == ItineraryStatus.ACCEPTED
    assert itinerary.accepted_at is not None
