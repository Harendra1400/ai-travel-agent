"""Database migration and LangGraph checkpoint bootstrap."""

import asyncio

from alembic import command
from alembic.config import Config
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.core.config import get_settings


def migrate_database() -> None:
    """Apply versioned relational schema migrations to the configured database."""
    command.upgrade(Config("alembic.ini"), "head")


async def setup_checkpoints() -> None:
    """Create the tables managed by LangGraph's PostgreSQL checkpointer."""
    checkpoint_url = get_settings().database_url.replace(
        "postgresql+psycopg://",
        "postgresql://",
    )
    async with AsyncPostgresSaver.from_conn_string(checkpoint_url) as checkpointer:
        await checkpointer.setup()


if __name__ == "__main__":
    migrate_database()
    asyncio.run(setup_checkpoints())
