"""Agent-run queue, status, and event routes."""

from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sse_starlette.sse import EventSourceResponse

from app.dependencies import CurrentUserDep, SessionDep
from app.infrastructure.redis import AGENT_EVENT_PREFIX, redis_client
from app.schemas.agent_run import AgentRunCreate, AgentRunRead
from app.services.agent_runs import (
    cancel_agent_run,
    create_agent_run,
    get_agent_run,
)

router = APIRouter(prefix="/v1/agent-runs", tags=["agent-runs"])


@router.post("", response_model=AgentRunRead, status_code=202)
async def post_agent_run(
    payload: AgentRunCreate,
    session: SessionDep,
    user: CurrentUserDep,
) -> AgentRunRead:
    """Persist and enqueue an asynchronous planning workflow."""
    run = await create_agent_run(session, user, payload)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    return AgentRunRead.model_validate(run)


@router.get("/{run_id}", response_model=AgentRunRead)
async def get_agent_run_status(
    run_id: UUID,
    session: SessionDep,
    user: CurrentUserDep,
) -> AgentRunRead:
    """Read the durable status of an owned agent run."""
    run = await get_agent_run(session, user, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Agent run not found")
    return AgentRunRead.model_validate(run)


@router.post("/{run_id}/cancel", response_model=AgentRunRead)
async def post_cancel_agent_run(
    run_id: UUID,
    session: SessionDep,
    user: CurrentUserDep,
) -> AgentRunRead:
    """Cancel an owned queued, running, or approval-waiting run."""
    run = await cancel_agent_run(session, user, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Agent run not found")
    return AgentRunRead.model_validate(run)


@router.get("/{run_id}/events")
async def get_agent_run_events(
    run_id: UUID,
    session: SessionDep,
    user: CurrentUserDep,
) -> EventSourceResponse:
    """Stream transient progress after verifying durable run ownership."""
    if await get_agent_run(session, user, run_id) is None:
        raise HTTPException(status_code=404, detail="Agent run not found")

    async def events() -> AsyncIterator[dict[str, str]]:
        async with redis_client.pubsub() as pubsub:
            await pubsub.subscribe(f"{AGENT_EVENT_PREFIX}{run_id}")
            async for message in pubsub.listen():
                if message["type"] == "message":
                    yield {"event": "agent-run", "data": str(message["data"])}

    return EventSourceResponse(events())
