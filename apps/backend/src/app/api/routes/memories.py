"""User-governed long-term memory endpoints."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Response, status

from app.dependencies import CurrentUserDep, SessionDep, SettingsDep
from app.schemas.memory import MemoryCreate, MemoryRead
from app.services.memories import create_memory, delete_memory, list_memories

router = APIRouter(prefix="/v1/memories", tags=["memories"])


@router.post("", response_model=MemoryRead, status_code=201)
async def post_memory(
    payload: MemoryCreate,
    session: SessionDep,
    user: CurrentUserDep,
    settings: SettingsDep,
) -> MemoryRead:
    """Create a memory only for resources owned by the current user."""
    memory = await create_memory(session, user, payload, settings)
    if memory is None:
        raise HTTPException(status_code=404, detail="Trip or conversation not found")
    return MemoryRead.model_validate(memory)


@router.get("", response_model=list[MemoryRead])
async def get_memories(
    session: SessionDep,
    user: CurrentUserDep,
) -> list[MemoryRead]:
    """List the current user's active memories."""
    return [
        MemoryRead.model_validate(memory)
        for memory in await list_memories(session, user)
    ]


@router.delete("/{memory_id}", status_code=204)
async def remove_memory(
    memory_id: UUID,
    session: SessionDep,
    user: CurrentUserDep,
) -> Response:
    """Permanently remove an owned memory and vector representation."""
    if not await delete_memory(session, user, memory_id):
        raise HTTPException(status_code=404, detail="Memory not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
