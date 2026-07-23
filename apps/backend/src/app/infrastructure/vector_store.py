"""Qdrant adapter for governed semantic memory."""

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from app.core.config import get_settings


class MemoryVectorStore:
    """Tenant-filtered semantic-memory search boundary."""

    def __init__(self) -> None:
        settings = get_settings()
        api_key = (
            settings.qdrant_api_key.get_secret_value()
            if settings.qdrant_api_key
            else None
        )
        self._client = AsyncQdrantClient(
            url=settings.qdrant_url,
            api_key=api_key,
        )
        self._collection = settings.qdrant_memory_collection
        self._dimensions = settings.embedding_dimensions

    async def ensure_collection(self) -> None:
        """Create the vector collection on first use with cosine distance."""
        if not await self._client.collection_exists(self._collection):
            await self._client.create_collection(
                collection_name=self._collection,
                vectors_config=VectorParams(
                    size=self._dimensions,
                    distance=Distance.COSINE,
                ),
            )

    async def upsert(
        self,
        *,
        memory_id: str,
        user_id: str,
        vector: list[float],
        payload: dict[str, object],
    ) -> None:
        """Index one memory with mandatory tenant ownership payload."""
        await self.ensure_collection()
        await self._client.upsert(
            collection_name=self._collection,
            points=[
                PointStruct(
                    id=memory_id,
                    vector=vector,
                    payload={**payload, "user_id": user_id},
                )
            ],
            wait=True,
        )

    async def search(
        self,
        *,
        user_id: str,
        vector: list[float],
        limit: int = 5,
    ) -> list[dict[str, object]]:
        """Search only memory points owned by the authenticated user."""
        result = await self._client.query_points(
            collection_name=self._collection,
            query=vector,
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="user_id",
                        match=MatchValue(value=user_id),
                    )
                ]
            ),
            limit=limit,
            with_payload=True,
        )
        return [point.payload or {} for point in result.points]

    async def delete(self, memory_id: str) -> None:
        """Remove one vector point by its application UUID."""
        if await self._client.collection_exists(self._collection):
            await self._client.delete(
                collection_name=self._collection,
                points_selector=[memory_id],
                wait=True,
            )

    async def close(self) -> None:
        """Release the underlying HTTP client."""
        await self._client.close()
