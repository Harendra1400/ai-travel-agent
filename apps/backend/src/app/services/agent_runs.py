"""Durable agent-run application service."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AgentRun, Conversation, Trip, User
from app.db.models.enums import AgentRunStatus
from app.schemas.agent_run import AgentRunCreate
from app.services.outbox import queue_agent_run_event


async def create_agent_run(
    session: AsyncSession,
    user: User,
    payload: AgentRunCreate,
) -> AgentRun | None:
    """Persist a queued run and its outbox event in one transaction."""
    conversation = await session.scalar(
        select(Conversation).where(
            Conversation.id == payload.conversation_id,
            Conversation.user_id == user.id,
        )
    )
    if conversation is None:
        return None

    existing = await session.scalar(
        select(AgentRun).where(
            AgentRun.user_id == user.id,
            AgentRun.idempotency_key == payload.idempotency_key,
        )
    )
    if existing is not None:
        return existing
    if payload.trip_id is not None:
        trip = await session.scalar(
            select(Trip).where(
                Trip.id == payload.trip_id,
                Trip.user_id == user.id,
            )
        )
        if trip is None or (
            conversation.trip_id is not None and conversation.trip_id != payload.trip_id
        ):
            return None

    run = AgentRun(
        user_id=user.id,
        conversation_id=payload.conversation_id,
        trip_id=payload.trip_id,
        graph_name="travel-planner",
        graph_version="1",
        model_name=None,
        idempotency_key=payload.idempotency_key,
        status=AgentRunStatus.QUEUED,
        queued_at=datetime.now(UTC),
        input_payload=payload.model_dump(mode="json"),
    )
    session.add(run)
    await session.flush()
    queue_agent_run_event(session, run.id)
    await session.commit()
    return run


async def get_agent_run(
    session: AsyncSession,
    user: User,
    run_id: UUID,
) -> AgentRun | None:
    """Load an agent run only when owned by the authenticated user."""
    run: AgentRun | None = await session.scalar(
        select(AgentRun).where(
            AgentRun.id == run_id,
            AgentRun.user_id == user.id,
        )
    )
    return run


async def cancel_agent_run(
    session: AsyncSession,
    user: User,
    run_id: UUID,
) -> AgentRun | None:
    """Cancel an owned non-terminal run; workers discard late model results."""
    run = await session.scalar(
        select(AgentRun)
        .where(AgentRun.id == run_id, AgentRun.user_id == user.id)
        .with_for_update()
    )
    if run is None:
        return None
    if run.status not in {
        AgentRunStatus.COMPLETED,
        AgentRunStatus.FAILED,
        AgentRunStatus.CANCELLED,
    }:
        run.status = AgentRunStatus.CANCELLED
        run.completed_at = datetime.now(UTC)
        await session.flush()
    return run
