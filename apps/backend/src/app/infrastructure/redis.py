"""Redis connection lifecycle and agent-run queue."""

from redis.asyncio import Redis

from app.core.config import get_settings

AGENT_RUN_STREAM = "travel-agent:runs"
TOOL_CALL_STREAM = "travel-agent:tool-calls"
MEMORY_INDEX_STREAM = "travel-agent:memory-index"
AGENT_EVENT_PREFIX = "travel-agent:events:"

settings = get_settings()
redis_client = Redis.from_url(settings.redis_url, decode_responses=True)


async def enqueue_agent_run(run_id: str) -> None:
    """Publish a durable agent-run identifier to the worker stream."""
    await redis_client.xadd(AGENT_RUN_STREAM, {"run_id": run_id})


async def enqueue_tool_call(tool_call_id: str) -> None:
    """Publish a durable tool-call identifier to the worker stream."""
    await redis_client.xadd(TOOL_CALL_STREAM, {"tool_call_id": tool_call_id})


async def enqueue_memory_index(memory_id: str) -> None:
    """Publish a durable semantic-memory indexing identifier."""
    await redis_client.xadd(MEMORY_INDEX_STREAM, {"memory_id": memory_id})


async def publish_agent_event(run_id: str, event: str) -> None:
    """Publish a transient progress event for connected clients."""
    await redis_client.publish(f"{AGENT_EVENT_PREFIX}{run_id}", event)


async def close_redis() -> None:
    """Close Redis connections during application shutdown."""
    await redis_client.aclose()
