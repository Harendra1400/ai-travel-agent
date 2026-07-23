"""Redis-stream worker for durable LangGraph execution."""

import asyncio
import logging
import socket
from contextlib import suppress
from datetime import UTC, datetime
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from sqlalchemy import select

from app.agents import build_travel_graph
from app.core.config import get_settings
from app.db.models import AgentRun, ToolCall
from app.db.models.enums import AgentRunStatus, ToolCallStatus
from app.db.session import async_session_factory
from app.infrastructure.redis import (
    AGENT_RUN_STREAM,
    MEMORY_INDEX_STREAM,
    TOOL_CALL_STREAM,
    publish_agent_event,
    redis_client,
)
from app.services.itineraries import persist_itinerary
from app.services.memories import index_memory, retrieve_relevant_memories
from app.services.outbox import dispatch_outbox_batch
from app.services.tool_calls import execute_tool_call, stage_requested_tools

CONSUMER_GROUP = "travel-agent-workers"
CONSUMER_NAME = f"{socket.gethostname()}-{id(object())}"
CLAIM_IDLE_MS = 60_000
logger = logging.getLogger(__name__)


async def process_run(run_id: UUID) -> None:
    """Execute one run and persist its terminal state."""
    async with async_session_factory() as session:
        run = await session.scalar(
            select(AgentRun).where(AgentRun.id == run_id).with_for_update()
        )
        if run is None or run.status != AgentRunStatus.QUEUED:
            return
        run.status = AgentRunStatus.RUNNING
        run.started_at = datetime.now(UTC)
        run.model_name = get_settings().openai_model
        await session.commit()

        await publish_agent_event(str(run_id), '{"status":"running"}')
        try:
            checkpoint_url = get_settings().database_url.replace(
                "postgresql+psycopg://",
                "postgresql://",
            )
            successful_calls = list(
                (
                    await session.scalars(
                        select(ToolCall).where(
                            ToolCall.agent_run_id == run.id,
                            ToolCall.status == ToolCallStatus.SUCCEEDED,
                        )
                    )
                ).all()
            )
            tool_context = [
                (
                    f"Tool result {item.mcp_server}/{item.tool_name}: "
                    f"{item.response_payload}"
                )
                for item in successful_calls
            ]
            memory_context = await retrieve_relevant_memories(
                user_id=run.user_id,
                query=str(run.input_payload["request"]),
                settings=get_settings(),
            )
            async with AsyncPostgresSaver.from_conn_string(
                checkpoint_url
            ) as checkpointer:
                result = await build_travel_graph(checkpointer).ainvoke(
                    {
                        "request": str(run.input_payload["request"]),
                        "user_id": str(run.user_id),
                        "trip_id": str(run.trip_id) if run.trip_id else None,
                        "context": [
                            *(f"User memory: {item}" for item in memory_context),
                            *tool_context,
                        ],
                    },
                    {"configurable": {"thread_id": str(run_id)}},
                )
            await session.refresh(run)
            if run.status == AgentRunStatus.CANCELLED:
                return
            run.output_payload = jsonable_encoder(dict(result))
            validation_errors = result.get("validation_errors", [])
            if validation_errors:
                run.status = AgentRunStatus.FAILED
                run.error_code = "plan_validation_failed"
                run.error_message = "; ".join(validation_errors)[:2000]
                run.completed_at = datetime.now(UTC)
            else:
                requested_tools = result.get("requested_tools", [])
                queued, approvals = await stage_requested_tools(
                    session,
                    run,
                    requested_tools,
                    get_settings(),
                )
                if queued:
                    run.status = AgentRunStatus.RUNNING
                elif approvals:
                    run.status = AgentRunStatus.WAITING_FOR_USER
                else:
                    await persist_itinerary(
                        session,
                        run,
                        plan=result["plan"],
                        items=result.get("itinerary_items", []),
                    )
                    run.status = AgentRunStatus.COMPLETED
                    run.completed_at = datetime.now(UTC)
        except Exception as exc:
            run.status = AgentRunStatus.FAILED
            run.error_code = type(exc).__name__
            run.error_message = "Agent execution failed"
            run.completed_at = datetime.now(UTC)
            logger.exception(
                "agent_run_failed",
                extra={"run_id": str(run.id)},
            )
        finally:
            await session.commit()
            await publish_agent_event(
                str(run_id),
                f'{{"status":"{run.status.value}"}}',
            )


async def run_worker() -> None:
    """Dispatch the outbox and consume new or abandoned run messages."""
    streams = (AGENT_RUN_STREAM, TOOL_CALL_STREAM, MEMORY_INDEX_STREAM)
    for stream in streams:
        with suppress(Exception):
            await redis_client.xgroup_create(
                stream,
                CONSUMER_GROUP,
                id="0",
                mkstream=True,
            )

    while True:
        async with async_session_factory() as session:
            await dispatch_outbox_batch(session)

        recovered_batches: list[tuple[str, list[tuple[str, dict[str, str]]]]] = []
        for stream in streams:
            claimed = await redis_client.xautoclaim(
                stream,
                CONSUMER_GROUP,
                CONSUMER_NAME,
                min_idle_time=CLAIM_IDLE_MS,
                start_id="0-0",
                count=10,
            )
            recovered_batches.append((stream, claimed[1] if len(claimed) > 1 else []))
        messages = await redis_client.xreadgroup(
            CONSUMER_GROUP,
            CONSUMER_NAME,
            {stream: ">" for stream in streams},
            count=10,
            block=5000,
        )
        batches = [*recovered_batches, *messages]
        for stream, entries in batches:
            for message_id, fields in entries:
                try:
                    if "run_id" in fields:
                        run_id = UUID(fields["run_id"])
                        await process_run(run_id)
                        event_id = str(run_id)
                    elif "tool_call_id" in fields:
                        tool_call_id = UUID(fields["tool_call_id"])
                        async with async_session_factory() as session:
                            await execute_tool_call(
                                session,
                                tool_call_id,
                                get_settings(),
                            )
                        event_id = str(tool_call_id)
                    else:
                        memory_id = UUID(fields["memory_id"])
                        async with async_session_factory() as session:
                            await index_memory(
                                session,
                                memory_id,
                                get_settings(),
                            )
                        event_id = str(memory_id)
                except Exception:
                    logger.exception(
                        "background_job_failed",
                        extra={"fields": fields},
                    )
                else:
                    await redis_client.xack(
                        stream,
                        CONSUMER_GROUP,
                        message_id,
                    )
                    await publish_agent_event(
                        event_id,
                        '{"status":"processed"}',
                    )


if __name__ == "__main__":
    asyncio.run(run_worker())
