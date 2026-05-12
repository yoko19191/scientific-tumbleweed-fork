"""Application-owned PostgreSQL access.

This module hosts the shared ``asyncpg`` connection pool used by repositories
migrated away from SQLite. LangGraph's own checkpointer/store manage their own
connections via ``langgraph-checkpoint-postgres`` — this module is only for
*our* tables (``users``, ``user_memory``, ``tool_cache``, ``channel_threads``).

Usage::

    from deerflow.db import get_pool

    async with get_pool().acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
"""

from deerflow.db.pool import (
    close_pool,
    get_pool,
    init_pool,
    is_initialized,
)
from deerflow.db.setup import ensure_schema

__all__ = [
    "close_pool",
    "ensure_schema",
    "get_pool",
    "init_pool",
    "is_initialized",
]
