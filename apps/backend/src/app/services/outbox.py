"""Transactional outbox publication for durable background work."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import OutboxEvent
from app.db.models.enums import OutboxStatus
from app.infrastructure.redis import (
    enqueue_agent_run,
    enqueue_memory_index,
    enqueue_tool_call,
)

AGENT_RUN_QUEUED = "agent-run.queued"
TOOL_CALL_QUEUED = "tool-call.queued"
MEMORY_INDEX_REQUESTED = "memory.index-requested"


def queue_agent_run_event(session: AsyncSession, run_id: UUID) -> None:
    """Stage a queue event in the same transaction as its agent run."""
    session.add(
        OutboxEvent(
            aggregate_type="agent_run",
            aggregate_id=run_id,
            event_type=AGENT_RUN_QUEUED,
            payload={"run_id": str(run_id)},
            status=OutboxStatus.PENDING,
            available_at=datetime.now(UTC),
        )
    )


def queue_tool_call_event(session: AsyncSession, tool_call_id: UUID) -> None:
    """Stage a tool-call job in the current database transaction."""
    session.add(
        OutboxEvent(
            aggregate_type="tool_call",
            aggregate_id=tool_call_id,
            event_type=TOOL_CALL_QUEUED,
            payload={"tool_call_id": str(tool_call_id)},
            status=OutboxStatus.PENDING,
            available_at=datetime.now(UTC),
        )
    )


def queue_memory_index_event(session: AsyncSession, memory_id: UUID) -> None:
    """Stage semantic indexing after the memory row commits."""
    session.add(
        OutboxEvent(
            aggregate_type="memory",
            aggregate_id=memory_id,
            event_type=MEMORY_INDEX_REQUESTED,
            payload={"memory_id": str(memory_id)},
            status=OutboxStatus.PENDING,
            available_at=datetime.now(UTC),
        )
    )


async def dispatch_outbox_batch(
    session: AsyncSession,
    *,
    batch_size: int = 50,
) -> int:
    """Publish due events with at-least-once delivery and row-level claiming."""
    events = list(
        (
            await session.scalars(
                select(OutboxEvent)
                .where(
                    OutboxEvent.status.in_((OutboxStatus.PENDING, OutboxStatus.FAILED)),
                    OutboxEvent.available_at <= datetime.now(UTC),
                )
                .order_by(OutboxEvent.created_at)
                .limit(batch_size)
                .with_for_update(skip_locked=True)
            )
        ).all()
    )
    published = 0
    for event in events:
        event.status = OutboxStatus.PROCESSING
        event.attempts += 1
        try:
            if event.event_type == AGENT_RUN_QUEUED:
                await enqueue_agent_run(str(event.aggregate_id))
            elif event.event_type == TOOL_CALL_QUEUED:
                await enqueue_tool_call(str(event.aggregate_id))
            elif event.event_type == MEMORY_INDEX_REQUESTED:
                await enqueue_memory_index(str(event.aggregate_id))
            else:
                raise ValueError(f"Unsupported outbox event: {event.event_type}")
            event.status = OutboxStatus.PUBLISHED
            event.processed_at = datetime.now(UTC)
            event.last_error = None
            published += 1
        except Exception as exc:
            event.status = OutboxStatus.FAILED
            event.last_error = str(exc)[:2000]
    await session.commit()
    return published
