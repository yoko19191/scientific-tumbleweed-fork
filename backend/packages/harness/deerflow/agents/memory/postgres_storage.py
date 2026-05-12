"""PostgreSQL-backed memory storage.

Replaces the file-based :class:`FileMemoryStorage` that writes
``.deer-flow/memory.json`` and ``.deer-flow/users/{user_id}/memory.json``.

Design notes
------------
- The ``MemoryStorage`` interface is **synchronous** (called from both
  sync prompt-generation paths and async FastAPI routers via threadpool).
  We therefore use a ``psycopg_pool.ConnectionPool`` rather than asyncpg.
- Global memory (no ``user_id``) is stored under the sentinel
  ``user_id = '__global__'`` so the primary key stays NOT NULL.
- Updates go through ``INSERT … ON CONFLICT DO UPDATE`` with a ``version``
  column bump, mirroring the optimistic-locking pattern LangGraph's
  store uses internally. Overwrites are last-writer-wins by design —
  consistent with the previous file-based storage.
- DSN resolution is identical to ``deerflow.db.pool`` so both the async
  (users, cache) and sync (memory) pools target the same database.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from typing import TYPE_CHECKING, Any

from deerflow.agents.memory.storage import (
    MemoryStorage,
    create_empty_memory,
    utc_now_iso_z,
)

if TYPE_CHECKING:
    from psycopg_pool import ConnectionPool

logger = logging.getLogger(__name__)

_GLOBAL_USER_ID = "__global__"


def _resolve_dsn() -> str:
    """Resolve the Postgres DSN the same way ``deerflow.db.pool`` does."""
    env_dsn = os.getenv("POSTGRES_DSN")
    if env_dsn:
        return env_dsn

    try:
        from deerflow.config.checkpointer_config import get_checkpointer_config

        cp_config = get_checkpointer_config()
        if cp_config and cp_config.type == "postgres" and cp_config.connection_string:
            conn_str = cp_config.connection_string
            if conn_str.startswith("$"):
                expanded = os.getenv(conn_str[1:])
                if expanded:
                    return expanded
            else:
                return conn_str
    except Exception:
        pass

    raise RuntimeError(
        "Cannot resolve Postgres DSN for PostgresMemoryStorage. "
        "Set POSTGRES_DSN or configure checkpointer.connection_string."
    )


class PostgresMemoryStorage(MemoryStorage):
    """Store memory as JSONB rows in the ``user_memory`` table.

    The schema is created by :func:`deerflow.db.setup.ensure_schema` at
    gateway startup.  This class assumes the table already exists.
    """

    def __init__(self) -> None:
        self._pool: ConnectionPool | None = None
        self._pool_lock = threading.Lock()
        # Local cache mirrors FileMemoryStorage's semantics: load() is cheap
        # to call repeatedly from prompt generation, so we cache by user_id
        # and invalidate on save. Version column lets us skip re-reads that
        # would see the same row.
        self._cache: dict[str, tuple[dict[str, Any], int]] = {}
        self._cache_lock = threading.Lock()

    # ------------------------------------------------------------------
    # Pool management
    # ------------------------------------------------------------------

    def _get_pool(self) -> ConnectionPool:
        """Lazily create the psycopg sync connection pool."""
        if self._pool is not None:
            return self._pool
        with self._pool_lock:
            if self._pool is not None:
                return self._pool
            from psycopg_pool import ConnectionPool

            dsn = _resolve_dsn()
            pool = ConnectionPool(
                conninfo=dsn,
                min_size=1,
                max_size=4,
                open=False,
                kwargs={"autocommit": True},
            )
            pool.open(wait=True, timeout=15.0)
            self._pool = pool
            logger.info("PostgresMemoryStorage pool ready")
            return pool

    @staticmethod
    def _scope_key(user_id: str | None) -> str:
        return user_id or _GLOBAL_USER_ID

    # ------------------------------------------------------------------
    # MemoryStorage interface
    # ------------------------------------------------------------------

    def load(self, user_id: str | None = None) -> dict[str, Any]:
        """Load memory for a user (or global), using an in-process cache."""
        key = self._scope_key(user_id)

        with self._cache_lock:
            cached = self._cache.get(key)
        if cached is not None:
            return cached[0]

        return self._fetch_and_cache(key)

    def reload(self, user_id: str | None = None) -> dict[str, Any]:
        """Force a database round-trip and refresh the cache."""
        key = self._scope_key(user_id)
        return self._fetch_and_cache(key)

    def _fetch_and_cache(self, key: str) -> dict[str, Any]:
        pool = self._get_pool()
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT data, version FROM user_memory WHERE user_id = %s",
                (key,),
            )
            row = cur.fetchone()

        if row is None:
            data = create_empty_memory()
            version = 0
        else:
            data = row[0] if isinstance(row[0], dict) else json.loads(row[0])
            version = int(row[1])

        with self._cache_lock:
            self._cache[key] = (data, version)
        return data

    def save(self, memory_data: dict[str, Any], user_id: str | None = None) -> bool:
        """Persist memory to Postgres and refresh the cache."""
        key = self._scope_key(user_id)

        # Mirror FileMemoryStorage's behaviour: stamp lastUpdated without
        # mutating the caller's dict, and only update the cache after the
        # database write succeeds.
        stamped = {**memory_data, "lastUpdated": utc_now_iso_z()}

        try:
            pool = self._get_pool()
            payload = json.dumps(stamped, ensure_ascii=False)
            with pool.connection() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO user_memory (user_id, data, version, updated_at)
                    VALUES (%s, %s::jsonb, 1, NOW())
                    ON CONFLICT (user_id) DO UPDATE
                        SET data = EXCLUDED.data,
                            version = user_memory.version + 1,
                            updated_at = NOW()
                    RETURNING version
                    """,
                    (key, payload),
                )
                row = cur.fetchone()
                new_version = int(row[0]) if row else 0
        except Exception:
            logger.exception("Failed to save memory to Postgres for user_id=%s", key)
            return False

        with self._cache_lock:
            self._cache[key] = (stamped, new_version)
        logger.info("Memory saved to Postgres (user_id=%s, version=%d)", key, new_version)
        return True

    # ------------------------------------------------------------------
    # Cleanup hook (used by tests)
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the underlying pool. Idempotent."""
        with self._pool_lock:
            if self._pool is not None:
                self._pool.close()
                self._pool = None
