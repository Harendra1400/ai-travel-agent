"""Human approval query and decision service."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AgentRun, Approval, AuditEvent, ToolCall, User
from app.db.models.enums import ApprovalStatus, ToolCallStatus
from app.schemas.approval import ApprovalDecision
from app.services.outbox import queue_tool_call_event


async def list_pending_approvals(
    session: AsyncSession,
    user: User,
) -> list[Approval]:
    """List unexpired decisions owned by the authenticated user."""
    result = await session.scalars(
        select(Approval)
        .where(
            Approval.user_id == user.id,
            Approval.status == ApprovalStatus.PENDING,
            Approval.expires_at > datetime.now(UTC),
        )
        .order_by(Approval.created_at)
    )
    return list(result)


async def decide_approval(
    session: AsyncSession,
    user: User,
    approval_id: UUID,
    payload: ApprovalDecision,
) -> Approval | None:
    """Approve or reject once using optimistic version enforcement."""
    approval = await session.scalar(
        select(Approval)
        .where(
            Approval.id == approval_id,
            Approval.user_id == user.id,
        )
        .with_for_update()
    )
    if approval is None:
        return None
    if approval.status != ApprovalStatus.PENDING:
        raise ValueError("Approval has already been decided")
    if approval.version != payload.version:
        raise ValueError("Approval version is stale")
    now = datetime.now(UTC)
    if approval.expires_at <= now:
        approval.status = ApprovalStatus.EXPIRED
        approval.version += 1
        await session.flush()
        raise ValueError("Approval has expired")

    approval.status = ApprovalStatus(payload.decision)
    approval.decided_at = now
    approval.decision_reason = payload.reason
    approval.version += 1
    tool_call = await session.get(ToolCall, approval.tool_call_id)
    run = await session.get(AgentRun, approval.agent_run_id)
    if tool_call is None or run is None:
        raise ValueError("Approval target no longer exists")
    if approval.status == ApprovalStatus.APPROVED:
        queue_tool_call_event(session, tool_call.id)
    else:
        tool_call.status = ToolCallStatus.DENIED

    session.add(
        AuditEvent(
            user_id=user.id,
            actor_subject=f"{user.auth_issuer}:{user.auth_subject}",
            action="approval.decided",
            resource_type="approval",
            resource_id=approval.id,
            outcome=approval.status.value,
            event_metadata={"tool_call_id": str(tool_call.id)},
        )
    )
    await session.flush()
    return approval
