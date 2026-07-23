"""Unit tests for tenant-scoped application services."""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.core.security import Principal
from app.db.models import AgentRun, Conversation, Preference, User
from app.db.models.enums import AgentRunStatus, MessageRole
from app.schemas.agent_run import AgentRunCreate
from app.schemas.conversation import ConversationCreate, MessageCreate
from app.schemas.preference import PreferenceUpdate
from app.schemas.trip import TripCreate
from app.services.agent_runs import (
    cancel_agent_run,
    create_agent_run,
    get_agent_run,
)
from app.services.conversations import (
    add_user_message,
    create_conversation,
    get_conversation,
)
from app.services.identity import get_or_create_user
from app.services.preferences import get_preferences, upsert_preferences
from app.services.trips import create_trip, get_trip, list_trips


def _session() -> MagicMock:
    session = MagicMock()
    session.scalar = AsyncMock()
    session.scalars = AsyncMock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.commit = AsyncMock()
    return session


def _user() -> User:
    return User(
        id=uuid4(),
        auth_issuer="test",
        auth_subject="user",
        email="user@example.com",
    )


async def test_trip_create_list_and_get_are_tenant_scoped() -> None:
    """Trip services always bind records and filters to the current user."""
    session = _session()
    user = _user()
    payload = TripCreate(title="Japan", destination_summary="Tokyo")
    trip = await create_trip(session, user, payload)
    assert trip.user_id == user.id
    session.scalars.return_value = [trip]
    assert await list_trips(session, user) == [trip]
    session.scalar.return_value = trip
    assert await get_trip(session, user, trip.id) is trip


async def test_conversation_and_message_are_owned_and_idempotent() -> None:
    """Conversation creation checks trip ownership and messages allocate order."""
    session = _session()
    user = _user()
    trip_id = uuid4()
    session.scalar.return_value = trip_id
    conversation = await create_conversation(
        session,
        user,
        ConversationCreate(trip_id=trip_id, title="Planning"),
    )
    assert conversation is not None
    assert conversation.user_id == user.id

    conversation.id = uuid4()
    session.scalar.side_effect = [conversation, None, 4]
    message = await add_user_message(
        session,
        user,
        conversation.id,
        MessageCreate(content="Window seat", idempotency_key="message-key"),
    )
    assert message is not None
    assert message.sequence_number == 5
    assert message.role == MessageRole.USER

    session.scalar.side_effect = None
    session.scalar.return_value = conversation
    assert await get_conversation(session, user, conversation.id) is conversation


async def test_conversation_rejects_unowned_trip() -> None:
    """A foreign trip identifier cannot be attached to a conversation."""
    session = _session()
    session.scalar.return_value = None
    result = await create_conversation(
        session,
        _user(),
        ConversationCreate(trip_id=uuid4()),
    )
    assert result is None


async def test_agent_run_creation_is_idempotent_and_transactional() -> None:
    """Run and outbox event are committed together after ownership checks."""
    session = _session()
    user = _user()
    conversation = Conversation(
        id=uuid4(),
        user_id=user.id,
        title="Planning",
    )
    session.scalar.side_effect = [conversation, None]
    payload = AgentRunCreate(
        conversation_id=conversation.id,
        request="Plan Rome",
        idempotency_key="request-key",
    )
    run = await create_agent_run(session, user, payload)
    assert run is not None
    assert run.status == AgentRunStatus.QUEUED
    assert run.idempotency_key == "request-key"
    session.commit.assert_awaited_once()
    assert session.add.call_count == 2

    existing = AgentRun(
        id=uuid4(),
        user_id=user.id,
        conversation_id=conversation.id,
        status=AgentRunStatus.QUEUED,
        graph_name="travel-planner",
        graph_version="1",
        idempotency_key="request-key",
        input_payload={},
        queued_at=datetime.now(UTC),
    )
    session.scalar.side_effect = [conversation, existing]
    assert await create_agent_run(session, user, payload) is existing
    session.scalar.side_effect = None
    session.scalar.return_value = existing
    assert await get_agent_run(session, user, existing.id) is existing

    existing.status = AgentRunStatus.RUNNING
    session.scalar.return_value = existing
    cancelled = await cancel_agent_run(session, user, existing.id)
    assert cancelled is existing
    assert existing.status == AgentRunStatus.CANCELLED
    assert existing.completed_at is not None


async def test_identity_provisioning_and_preferences_upsert() -> None:
    """OIDC identities provision once and preferences update in place."""
    session = _session()
    user = _user()
    session.execute.return_value = SimpleNamespace(scalar_one_or_none=lambda: user)
    principal = Principal("issuer", "subject", "person@example.com")
    assert await get_or_create_user(session, principal) is user

    session.execute.return_value = SimpleNamespace(scalar_one_or_none=lambda: None)
    created = await get_or_create_user(
        session,
        Principal("issuer", "new-subject", None),
    )
    assert created.email.endswith("@invalid.local")

    preference = Preference(id=uuid4(), user_id=user.id)
    session.scalar.return_value = preference
    assert await get_preferences(session, user) is preference
    updated = await upsert_preferences(
        session,
        user,
        PreferenceUpdate(home_airport="JFK", prefers_direct=True),
    )
    assert updated.home_airport == "JFK"
    assert updated.prefers_direct
