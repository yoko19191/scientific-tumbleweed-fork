"""Idempotent DDL for application-owned Postgres tables.

Called once at startup (typically in FastAPI lifespan, after ``init_pool``).
All DDL uses ``CREATE TABLE IF NOT EXISTS`` / ``CREATE INDEX IF NOT EXISTS``
so it is safe to call on every boot, including when tables already exist.

Style mirrors LangGraph's own ``AsyncPostgresSaver.setup()`` / ``AsyncPostgresStore.setup()``:

- ``timestamptz DEFAULT NOW()`` for all time columns
- No ORM / no Alembic — raw DDL, single source of truth
- Composite primary keys where natural, single-column btree index when we
  need to filter by a single component
- ``pg_advisory_lock`` around the whole setup so concurrent startup across
  multiple pods does not race on extension/table creation
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import asyncpg

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Advisory lock key — arbitrary but stable across processes.
# Picked a fixed 64-bit int so pg_advisory_lock() is deterministic.
# ---------------------------------------------------------------------------

_SETUP_ADVISORY_LOCK_KEY = 7260524_11_01  # date-derived: 2026-05-11 phase 01


# ---------------------------------------------------------------------------
# DDL statements — phase by phase
# ---------------------------------------------------------------------------

_EXTENSIONS_DDL = [
    # pgvector — available for future embeddings / ANN features.
    "CREATE EXTENSION IF NOT EXISTS vector",
    # pg_search — ParadeDB BM25 full-text search.
    "CREATE EXTENSION IF NOT EXISTS pg_search",
    # pg_stat_statements — query-level observability.
    "CREATE EXTENSION IF NOT EXISTS pg_stat_statements",
]

# Phase 2: users (replaces .deer-flow/users.db).
_USERS_DDL = [
    """
    CREATE TABLE IF NOT EXISTS users (
        id               text PRIMARY KEY,
        email            text NOT NULL,
        username         text NOT NULL DEFAULT '',
        display_name     text NOT NULL DEFAULT '',
        password_hash    text,
        system_role      text NOT NULL DEFAULT 'user',
        created_at       timestamptz NOT NULL DEFAULT NOW(),
        oauth_provider   text,
        oauth_id         text,
        needs_setup      boolean NOT NULL DEFAULT false,
        token_version    integer NOT NULL DEFAULT 0
    )
    """,
    # Email and username uniqueness — mirrors the sqlite constraints.
    "CREATE UNIQUE INDEX IF NOT EXISTS users_email_key ON users (email)",
    "CREATE UNIQUE INDEX IF NOT EXISTS users_username_key ON users (username)",
    # OAuth identity uniqueness — partial index mirroring the sqlite setup.
    """
    CREATE UNIQUE INDEX IF NOT EXISTS idx_users_oauth_identity
        ON users (oauth_provider, oauth_id)
        WHERE oauth_provider IS NOT NULL AND oauth_id IS NOT NULL
    """,
]


# Phase 3: user_memory (replaces .deer-flow/memory.json and
# .deer-flow/users/{user_id}/memory.json).
#
# ``user_id`` is the natural key. For the legacy "global" memory (no user
# context), we use the sentinel string '__global__' so the primary key stays
# NOT NULL and the query path is uniform.
_USER_MEMORY_DDL = [
    """
    CREATE TABLE IF NOT EXISTS user_memory (
        user_id     text PRIMARY KEY,
        data        jsonb NOT NULL DEFAULT '{}'::jsonb,
        version     integer NOT NULL DEFAULT 0,
        updated_at  timestamptz NOT NULL DEFAULT NOW()
    )
    """,
    # GIN on the whole JSONB for future @>/? queries. Cheap on a tiny table
    # and matches the style LangGraph uses for its JSONB columns.
    "CREATE INDEX IF NOT EXISTS idx_user_memory_data_gin ON user_memory USING gin (data)",
]


# Phase 4: tool_cache (replaces .deer-flow/cache/academic_search.db and
# any other sqlite TTL caches that share the same shape).
#
# Shape mirrors the sqlite ``cache_entries`` table from
# ``community/semantic_scholar/cache.py`` so the application code can
# swap backends without schema re-shaping.
_TOOL_CACHE_DDL = [
    """
    CREATE TABLE IF NOT EXISTS tool_cache (
        cache_key   text PRIMARY KEY,
        tool_name   text NOT NULL,
        value_json  jsonb NOT NULL,
        created_at  timestamptz NOT NULL DEFAULT NOW(),
        expires_at  timestamptz NOT NULL
    )
    """,
    # Partial index on expires_at — matches the LangGraph ``store`` table
    # pattern. Cheap maintenance and perfect for the periodic vacuum sweep.
    "CREATE INDEX IF NOT EXISTS idx_tool_cache_expires_at ON tool_cache (expires_at)",
    "CREATE INDEX IF NOT EXISTS idx_tool_cache_tool_name ON tool_cache (tool_name)",
]


# Phase 5: channel_threads (replaces .deer-flow/channels/store.json).
#
# One row per IM conversation mapping. The natural key is the composite
# ``<channel>:<chat_id>[:<topic_id>]`` produced by the old store code;
# keeping it as a single text PRIMARY KEY keeps callers unchanged.
_CHANNEL_THREADS_DDL = [
    """
    CREATE TABLE IF NOT EXISTS channel_threads (
        key         text PRIMARY KEY,
        thread_id   text NOT NULL,
        user_id     text NOT NULL DEFAULT '',
        created_at  timestamptz NOT NULL DEFAULT NOW(),
        updated_at  timestamptz NOT NULL DEFAULT NOW()
    )
    """,
    # Used by the "remove all mappings for a chat" path which scans by prefix.
    "CREATE INDEX IF NOT EXISTS idx_channel_threads_key_prefix ON channel_threads (key text_pattern_ops)",
]


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


async def ensure_schema(pool: asyncpg.Pool | None = None) -> None:
    """Create or upgrade the application-owned schema.

    Runs all DDL inside a transaction protected by a session-level advisory
    lock so concurrent pods starting up cannot race on CREATE EXTENSION.
    """
    if pool is None:
        from deerflow.db.pool import get_pool

        pool = get_pool()

    async with pool.acquire() as conn:
        # Acquire advisory lock (auto-released when transaction commits).
        # We use pg_advisory_xact_lock inside a transaction block.
        async with conn.transaction():
            await conn.execute(
                "SELECT pg_advisory_xact_lock($1)",
                _SETUP_ADVISORY_LOCK_KEY,
            )
            logger.info("Running application schema setup")

            for ddl in _EXTENSIONS_DDL:
                await conn.execute(ddl)

            for ddl in _USERS_DDL:
                await conn.execute(ddl)

            for ddl in _USER_MEMORY_DDL:
                await conn.execute(ddl)

            for ddl in _TOOL_CACHE_DDL:
                await conn.execute(ddl)

            for ddl in _CHANNEL_THREADS_DDL:
                await conn.execute(ddl)

            logger.info("Application schema setup complete")
