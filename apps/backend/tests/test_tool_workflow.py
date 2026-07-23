"""Durability and human-approval tests for MCP tool execution."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from pydantic import HttpUrl

from app.core.config import MCPServerSettings, MCPToolSettings, Settings
from app.db.models import AgentRun, Approval, OutboxEvent, ToolCall, User
from app.db.models.enums import (
    AgentRunStatus,
    ApprovalStatus,
    OutboxStatus,
    ToolCallStatus,
    ToolRisk,
)
from app.schemas.approval import ApprovalDecision
from app.services.approvals import decide_approval, list_pending_approvals
from app.services.outbox import dispatch_outbox_batch
from app.services.tool_calls import execute_tool_call, stage_requested_tools


def _run() -> AgentRun:
    return AgentRun(
        id=uuid4(),
        user_id=uuid4(),
        conversation_id=uuid4(),
        status=AgentRunStatus.RUNNING,
        graph_name="travel-planner",
        graph_version="1",
        idempotency_key="request-key",
        input_payload={"request": "Plan a trip"},
        queued_at=datetime.now(UTC),
    )


def _session() -> MagicMock:
    session = MagicMock()
    session.scalar = AsyncMock()
    session.scalars = AsyncMock()
    session.get = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.delete = AsyncMock()
    return session


async def test_stage_tools_queues_reads_and_requires_financial_approval() -> None:
    """Model proposals become durable calls only after exact policy resolution."""
    session = _session()
    session.scalar.side_effect = [0, None, None]
    run = _run()
    settings = Settings(
        mcp_servers={
            "travel": MCPServerSettings(url=HttpUrl("https://mcp.example.com"))
        },
        mcp_tools=[
            MCPToolSettings(server="travel", tool="search", risk="read"),
            MCPToolSettings(server="travel", tool="book", risk="financial"),
        ],
    )
    queued, approvals = await stage_requested_tools(
        session,
        run,
        [
            {"server": "travel", "tool": "search", "arguments": {"q": "JFK"}},
            {"server": "travel", "tool": "book", "arguments": {"offer": "1"}},
        ],
        settings,
    )
    assert (queued, approvals) == (1, 1)
    assert run.status == AgentRunStatus.WAITING_FOR_USER
    added = [call.args[0] for call in session.add.call_args_list]
    assert sum(isinstance(item, ToolCall) for item in added) == 2
    assert any(isinstance(item, Approval) for item in added)
    assert any(isinstance(item, OutboxEvent) for item in added)


async def test_execute_read_tool_requeues_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A successful read tool stores its result and continues the agent run."""
    session = _session()
    run = _run()
    call = ToolCall(
        id=uuid4(),
        agent_run_id=run.id,
        sequence_number=1,
        mcp_server="travel",
        tool_name="search",
        risk=ToolRisk.READ,
        status=ToolCallStatus.PENDING,
        request_payload={"q": "JFK"},
        idempotency_key="tool-key",
    )
    session.scalar.return_value = call
    session.get.return_value = run
    gateway_call = AsyncMock(return_value={"content": [{"text": "result"}]})
    monkeypatch.setattr(
        "app.services.tool_calls.MCPGateway.call_tool",
        gateway_call,
    )
    settings = Settings(
        mcp_servers={
            "travel": MCPServerSettings(url=HttpUrl("https://mcp.example.com"))
        },
        mcp_tools=[MCPToolSettings(server="travel", tool="search", risk="read")],
    )
    await execute_tool_call(session, call.id, settings)
    assert call.status == ToolCallStatus.SUCCEEDED
    assert run.status == AgentRunStatus.QUEUED
    assert call.response_payload == {"content": [{"text": "result"}]}
    assert any(
        isinstance(item.args[0], OutboxEvent) for item in session.add.call_args_list
    )


async def test_execute_side_effect_without_approval_is_denied() -> None:
    """Write and financial calls fail closed when approval is absent."""
    session = _session()
    call = ToolCall(
        id=uuid4(),
        agent_run_id=uuid4(),
        sequence_number=1,
        mcp_server="travel",
        tool_name="book",
        risk=ToolRisk.FINANCIAL,
        status=ToolCallStatus.PENDING,
        request_payload={},
        idempotency_key="tool-key",
    )
    session.scalar.side_effect = [call, None]
    await execute_tool_call(session, call.id, Settings())
    assert call.status == ToolCallStatus.DENIED
    assert call.error_code == "approval_required"


async def test_approval_decision_is_versioned_and_queues_tool() -> None:
    """A one-time approved decision stages exactly one execution event."""
    session = _session()
    user = User(
        id=uuid4(),
        auth_issuer="test",
        auth_subject="user",
        email="user@example.com",
    )
    run = _run()
    tool = ToolCall(
        id=uuid4(),
        agent_run_id=run.id,
        sequence_number=1,
        mcp_server="travel",
        tool_name="book",
        risk=ToolRisk.FINANCIAL,
        status=ToolCallStatus.PENDING,
        request_payload={},
        idempotency_key="book-key",
    )
    approval = Approval(
        id=uuid4(),
        user_id=user.id,
        agent_run_id=run.id,
        tool_call_id=tool.id,
        status=ApprovalStatus.PENDING,
        risk=ToolRisk.FINANCIAL,
        version=1,
        action_summary="Book",
        proposed_action={},
        expires_at=datetime.now(UTC) + timedelta(minutes=10),
    )
    session.scalar.return_value = approval
    session.get.side_effect = [tool, run]
    decided = await decide_approval(
        session,
        user,
        approval.id,
        ApprovalDecision(decision="approved", version=1),
    )
    assert decided is approval
    assert approval.status == ApprovalStatus.APPROVED
    assert approval.version == 2
    assert any(
        isinstance(call.args[0], OutboxEvent) for call in session.add.call_args_list
    )


async def test_pending_approval_query_and_outbox_dispatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pending decisions query cleanly and due events publish at least once."""
    session = _session()
    pending = MagicMock(spec=Approval)
    session.scalars.return_value = [pending]
    assert await list_pending_approvals(session, MagicMock()) == [pending]

    event = OutboxEvent(
        id=uuid4(),
        aggregate_type="agent_run",
        aggregate_id=uuid4(),
        event_type="agent-run.queued",
        payload={},
        status=OutboxStatus.PENDING,
        available_at=datetime.now(UTC),
        attempts=0,
    )
    session.scalars.return_value = SimpleNamespace(all=lambda: [event])
    enqueue = AsyncMock()
    monkeypatch.setattr("app.services.outbox.enqueue_agent_run", enqueue)
    assert await dispatch_outbox_batch(session) == 1
    enqueue.assert_awaited_once_with(str(event.aggregate_id))
    assert event.status == OutboxStatus.PUBLISHED
    assert event.attempts == 1
