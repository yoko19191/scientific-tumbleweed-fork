"""Application-owned PostgreSQL access.

Two layers live here:

- :mod:`deerflow.db.engine` — SQLAlchemy async engine + session factory.
  This is what new code should use.
- :mod:`deerflow.db.pool` — thin asyncpg pool adapter kept for callers
  that need a raw ``asyncpg.Pool`` (ensure_schema transactions, legacy
  call sites still being migrated).

LangGraph's own checkpointer/store manage their own connections via
``langgraph-checkpoint-postgres``. This module is only for *our* tables
(``users``, ``user_memory``, ``tool_cache``, ``channel_threads``).
"""

from deerflow.db.dsn import resolve_dsn, to_asyncpg_dsn, to_sqlalchemy_async_dsn
from deerflow.db.engine import (
    close_engine,
    close_sync_engine,
    get_engine,
    get_session_factory,
    get_sync_engine,
    get_sync_session_factory,
    init_engine,
    init_sync_engine,
    session_scope,
    sync_session_scope,
)
from deerflow.db.pool import (
    close_pool,
    get_pool,
    init_pool,
    is_initialized,
)
from deerflow.db.setup import ensure_schema

__all__ = [
    "close_engine",
    "close_pool",
    "close_sync_engine",
    "ensure_schema",
    "get_engine",
    "get_pool",
    "get_session_factory",
    "get_sync_engine",
    "get_sync_session_factory",
    "init_engine",
    "init_pool",
    "init_sync_engine",
    "is_initialized",
    "resolve_dsn",
    "session_scope",
    "sync_session_scope",
    "to_asyncpg_dsn",
    "to_sqlalchemy_async_dsn",
]
