"""PostgreSQL-backed, Qdrant-indexed user memory service."""

from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID

from openai import AsyncOpenAI
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.models import Conversation, Memory, Trip, User
from app.infrastructure.vector_store import MemoryVectorStore
from app.schemas.memory import MemoryCreate
from app.services.outbox import queue_memory_index_event


async def create_memory(
    session: AsyncSession,
    user: User,
    payload: MemoryCreate,
    settings: Settings,
) -> Memory | None:
    """Persist an owned memory and stage eventual vector indexing."""
    if (
        payload.trip_id is not None
        and await session.scalar(
            select(Trip.id).where(
                Trip.id == payload.trip_id,
                Trip.user_id == user.id,
            )
        )
        is None
    ):
        return None
    if (
        payload.conversation_id is not None
        and await session.scalar(
            select(Conversation.id).where(
                Conversation.id == payload.conversation_id,
                Conversation.user_id == user.id,
            )
        )
        is None
    ):
        return None
    memory = Memory(
        user_id=user.id,
        **payload.model_dump(),
        content_hash=sha256(payload.content.encode()).hexdigest(),
        embedding_model=settings.openai_embedding_model,
    )
    session.add(memory)
    await session.flush()
    queue_memory_index_event(session, memory.id)
    return memory


async def list_memories(
    session: AsyncSession,
    user: User,
) -> list[Memory]:
    """List active source-of-truth memories newest first."""
    result = await session.scalars(
        select(Memory)
        .where(
            Memory.user_id == user.id,
            or_(Memory.expires_at.is_(None), Memory.expires_at > datetime.now(UTC)),
        )
        .order_by(Memory.created_at.desc())
    )
    return list(result)


async def delete_memory(
    session: AsyncSession,
    user: User,
    memory_id: UUID,
) -> bool:
    """Delete an owned memory from Qdrant and PostgreSQL."""
    memory = await session.scalar(
        select(Memory).where(Memory.id == memory_id, Memory.user_id == user.id)
    )
    if memory is None:
        return False
    store = MemoryVectorStore()
    try:
        await store.delete(str(memory.id))
    finally:
        await store.close()
    await session.delete(memory)
    return True


async def index_memory(
    session: AsyncSession,
    memory_id: UUID,
    settings: Settings,
) -> None:
    """Embed and index an existing authoritative memory record."""
    memory = await session.get(Memory, memory_id)
    if memory is None or (
        memory.expires_at is not None and memory.expires_at <= datetime.now(UTC)
    ):
        return
    if settings.openai_api_key is None:
        raise RuntimeError("TRAVEL_AGENT_OPENAI_API_KEY is not configured")
    client = AsyncOpenAI(api_key=settings.openai_api_key.get_secret_value())
    response = await client.embeddings.create(
        model=settings.openai_embedding_model,
        input=memory.content,
        dimensions=settings.embedding_dimensions,
    )
    store = MemoryVectorStore()
    try:
        await store.upsert(
            memory_id=str(memory.id),
            user_id=str(memory.user_id),
            vector=response.data[0].embedding,
            payload={
                "content": memory.content,
                "kind": memory.kind.value,
                "trip_id": str(memory.trip_id) if memory.trip_id else None,
                "expires_at": (
                    memory.expires_at.isoformat() if memory.expires_at else None
                ),
            },
        )
    finally:
        await store.close()


async def retrieve_relevant_memories(
    *,
    user_id: UUID,
    query: str,
    settings: Settings,
    limit: int = 5,
) -> list[str]:
    """Retrieve semantically relevant memories with tenant filtering."""
    if settings.openai_api_key is None:
        return []
    client = AsyncOpenAI(api_key=settings.openai_api_key.get_secret_value())
    response = await client.embeddings.create(
        model=settings.openai_embedding_model,
        input=query,
        dimensions=settings.embedding_dimensions,
    )
    store = MemoryVectorStore()
    try:
        payloads = await store.search(
            user_id=str(user_id),
            vector=response.data[0].embedding,
            limit=limit,
        )
    finally:
        await store.close()
    now = datetime.now(UTC)
    return [
        str(payload["content"])
        for payload in payloads
        if "content" in payload
        and (
            payload.get("expires_at") is None
            or datetime.fromisoformat(str(payload["expires_at"])) > now
        )
    ]
