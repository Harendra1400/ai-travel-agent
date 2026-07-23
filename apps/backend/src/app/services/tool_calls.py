"""Policy-enforced MCP tool staging and execution."""

import json
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.state import RequestedTool
from app.core.config import Settings
from app.db.models import AgentRun, Approval, AuditEvent, ToolCall
from app.db.models.enums import (
    AgentRunStatus,
    ApprovalStatus,
    ToolCallStatus,
    ToolRisk,
)
from app.mcp_gateway.client import MCPGateway
from app.mcp_gateway.policy import resolve_tool_policy
from app.services.outbox import queue_agent_run_event, queue_tool_call_event


def _idempotency_key(run_id: UUID, request: RequestedTool) -> str:
    canonical = json.dumps(request, sort_keys=True, separators=(",", ":"))
    return sha256(f"{run_id}:{canonical}".encode()).hexdigest()


async def stage_requested_tools(
    session: AsyncSession,
    run: AgentRun,
    requests: list[RequestedTool],
    settings: Settings,
) -> tuple[int, int]:
    """Persist model-proposed calls after exact allow-list policy checks."""
    latest_sequence = await session.scalar(
        select(func.max(ToolCall.sequence_number)).where(
            ToolCall.agent_run_id == run.id
        )
    )
    sequence = latest_sequence or 0
    queued = 0
    approvals = 0

    for request in requests:
        policy = resolve_tool_policy(
            settings,
            request["server"],
            request["tool"],
        )
        key = _idempotency_key(run.id, request)
        existing = await session.scalar(
            select(ToolCall).where(ToolCall.idempotency_key == key)
        )
        if existing is not None:
            continue

        sequence += 1
        tool_call = ToolCall(
            agent_run_id=run.id,
            sequence_number=sequence,
            mcp_server=policy.server,
            tool_name=policy.tool,
            risk=policy.risk,
            status=ToolCallStatus.PENDING,
            request_payload=request["arguments"],
            idempotency_key=key,
        )
        session.add(tool_call)
        await session.flush()
        if policy.requires_human_approval:
            approval = Approval(
                user_id=run.user_id,
                agent_run_id=run.id,
                tool_call_id=tool_call.id,
                status=ApprovalStatus.PENDING,
                risk=policy.risk,
                action_summary=f"Allow {policy.server}/{policy.tool}",
                proposed_action={
                    "server": policy.server,
                    "tool": policy.tool,
                    "arguments": request["arguments"],
                },
                expires_at=datetime.now(UTC)
                + timedelta(minutes=settings.approval_ttl_minutes),
            )
            session.add(approval)
            approvals += 1
        else:
            queue_tool_call_event(session, tool_call.id)
            queued += 1

        session.add(
            AuditEvent(
                user_id=run.user_id,
                actor_subject="agent",
                action="tool_call.proposed",
                resource_type="tool_call",
                resource_id=tool_call.id,
                outcome=(
                    "approval_required" if policy.requires_human_approval else "queued"
                ),
                event_metadata={
                    "server": policy.server,
                    "tool": policy.tool,
                    "risk": policy.risk.value,
                },
            )
        )

    if approvals:
        run.status = AgentRunStatus.WAITING_FOR_USER
    return queued, approvals


async def execute_tool_call(
    session: AsyncSession,
    tool_call_id: UUID,
    settings: Settings,
) -> None:
    """Execute one queued call and schedule its run to continue."""
    tool_call = await session.scalar(
        select(ToolCall).where(ToolCall.id == tool_call_id).with_for_update()
    )
    if tool_call is None or tool_call.status != ToolCallStatus.PENDING:
        return

    if tool_call.risk != ToolRisk.READ:
        approval = await session.scalar(
            select(Approval).where(
                Approval.tool_call_id == tool_call.id,
                Approval.status == ApprovalStatus.APPROVED,
            )
        )
        if approval is None:
            tool_call.status = ToolCallStatus.DENIED
            tool_call.error_code = "approval_required"
            await session.commit()
            return
        approval.status = ApprovalStatus.CONSUMED

    tool_call.status = ToolCallStatus.RUNNING
    tool_call.started_at = datetime.now(UTC)
    await session.commit()

    gateway = MCPGateway(settings)
    run = await session.get(AgentRun, tool_call.agent_run_id)
    if run is None:
        return
    try:
        result = await gateway.call_tool(
            server=tool_call.mcp_server,
            tool=tool_call.tool_name,
            arguments=tool_call.request_payload,
            user_id=str(run.user_id),
            run_id=str(run.id),
        )
        tool_call.response_payload = result
        tool_call.status = ToolCallStatus.SUCCEEDED
        run.status = AgentRunStatus.QUEUED
        run.queued_at = datetime.now(UTC)
        queue_agent_run_event(session, run.id)
    except Exception as exc:
        tool_call.status = ToolCallStatus.FAILED
        tool_call.error_code = type(exc).__name__
        tool_call.error_message = str(exc)[:2000]
        run.status = AgentRunStatus.FAILED
        run.error_code = "tool_execution_failed"
        run.error_message = f"{tool_call.mcp_server}/{tool_call.tool_name} failed"
        run.completed_at = datetime.now(UTC)
    finally:
        tool_call.completed_at = datetime.now(UTC)
        session.add(
            AuditEvent(
                user_id=run.user_id,
                actor_subject="worker",
                action="tool_call.executed",
                resource_type="tool_call",
                resource_id=tool_call.id,
                outcome=tool_call.status.value,
                event_metadata={
                    "server": tool_call.mcp_server,
                    "tool": tool_call.tool_name,
                },
            )
        )
        await session.commit()
