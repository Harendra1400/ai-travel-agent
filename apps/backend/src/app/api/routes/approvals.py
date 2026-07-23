"""Human approval endpoints for agent-proposed side effects."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.dependencies import CurrentUserDep, SessionDep
from app.schemas.approval import ApprovalDecision, ApprovalRead
from app.services.approvals import decide_approval, list_pending_approvals

router = APIRouter(prefix="/v1/approvals", tags=["approvals"])


@router.get("", response_model=list[ApprovalRead])
async def get_pending_approvals(
    session: SessionDep,
    user: CurrentUserDep,
) -> list[ApprovalRead]:
    """List the current user's pending, unexpired approvals."""
    approvals = await list_pending_approvals(session, user)
    return [ApprovalRead.model_validate(item) for item in approvals]


@router.post("/{approval_id}/decision", response_model=ApprovalRead)
async def post_approval_decision(
    approval_id: UUID,
    payload: ApprovalDecision,
    session: SessionDep,
    user: CurrentUserDep,
) -> ApprovalRead:
    """Record one approve/reject decision."""
    try:
        approval = await decide_approval(session, user, approval_id, payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    if approval is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval not found",
        )
    return ApprovalRead.model_validate(approval)
