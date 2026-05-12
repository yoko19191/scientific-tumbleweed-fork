"""PostgreSQL-backed TTL cache.

Drop-in replacement for :class:`SQLiteTTLCache` backed by the shared
``tool_cache`` table. Exposes the same ``get`` / ``set`` interface so
callers in ``community/semantic_scholar/tools.py`` and
``community/academic_search/tools.py`` do not need to change.

Design notes
------------
- Uses the sync ``psycopg_pool.ConnectionPool`` to match the sync
  interface that ``tools.py`` callers rely on. (A single connection
  per cache instance would also work, but a small pool keeps idle
  costs low while supporting the occasional burst.)
- Keeps the same in-process "hot cache" (bounded LRU) as the SQLite
  version — this is the main hit path and we don't want to add a
  round-trip for every cache lookup.
- TTL is represented as ``expires_at timestamptz``; reads filter with
  ``expires_at > NOW()`` so expired rows are never returned and a
  background vacuum task periodically deletes them.
- ``INSERT … ON CONFLICT DO UPDATE`` provides the same semantics as
  sqlite's ``INSERT OR REPLACE``.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from psycopg_pool import ConnectionPool

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class _HotCacheEntry:
    value_json: str
    expires_at_unix: int


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
        "Cannot resolve Postgres DSN for PostgresTTLCache. "
        "Set POSTGRES_DSN or configure checkpointer.connection_string."
    )


# Shared pool across all PostgresTTLCache instances — one per DSN.
# Keeps the total connection count bounded even if many cache scopes
# (semantic_scholar + academic_search + future tools) share the DB.
_SHARED_POOLS: dict[str, ConnectionPool] = {}
_SHARED_POOLS_LOCK = threading.Lock()


def _get_shared_pool(dsn: str) -> ConnectionPool:
    from psycopg_pool import ConnectionPool

    with _SHARED_POOLS_LOCK:
        pool = _SHARED_POOLS.get(dsn)
        if pool is not None:
            return pool
        pool = ConnectionPool(
            conninfo=dsn,
            min_size=1,
            max_size=4,
            open=False,
            kwargs={"autocommit": True},
        )
        pool.open(wait=True, timeout=15.0)
        _SHARED_POOLS[dsn] = pool
        return pool


class PostgresTTLCache:
    """TTL cache stored in the ``tool_cache`` Postgres table.

    Exposes the same ``get`` / ``set`` / ``db_path`` surface as the
    legacy :class:`SQLiteTTLCache` so existing callers compile unchanged.
    """

    def __init__(self, hot_max_entries: int = 256, dsn: str | None = None) -> None:
        self._dsn = dsn or _resolve_dsn()
        self._hot_max_entries = max(1, hot_max_entries)
        self._hot_cache: OrderedDict[str, _HotCacheEntry] = OrderedDict()
        self._lock = threading.Lock()

    # The sqlite implementation exposed ``db_path``. We expose ``dsn``
    # for parity when the tests / diagnostics want the connection target.
    @property
    def db_path(self) -> str:
        return self._dsn

    # ------------------------------------------------------------------
    # Hot-cache helpers (identical to SQLiteTTLCache)
    # ------------------------------------------------------------------

    def _get_hot(self, cache_key: str) -> Any | None:
        now = int(time.time())
        with self._lock:
            entry = self._hot_cache.get(cache_key)
            if entry is None:
                return None
            if entry.expires_at_unix <= now:
                self._hot_cache.pop(cache_key, None)
                return None
            self._hot_cache.move_to_end(cache_key)
            return json.loads(entry.value_json)

    def _set_hot(self, cache_key: str, value_json: str, expires_at_unix: int) -> None:
        with self._lock:
            self._hot_cache[cache_key] = _HotCacheEntry(
                value_json=value_json, expires_at_unix=expires_at_unix
            )
            self._hot_cache.move_to_end(cache_key)
            while len(self._hot_cache) > self._hot_max_entries:
                self._hot_cache.popitem(last=False)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, cache_key: str) -> Any | None:
        hot = self._get_hot(cache_key)
        if hot is not None:
            return hot

        pool = _get_shared_pool(self._dsn)
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT value_json, EXTRACT(EPOCH FROM expires_at)::bigint AS expires_at_unix
                  FROM tool_cache
                 WHERE cache_key = %s AND expires_at > NOW()
                """,
                (cache_key,),
            )
            row = cur.fetchone()

        if row is None:
            return None

        value, expires_at_unix = row
        # psycopg returns JSONB columns as parsed Python objects; for hot
        # cache we keep a serialized form so memory footprint is bounded.
        if isinstance(value, (dict, list)):
            value_json = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
            parsed = value
        else:
            value_json = str(value)
            parsed = json.loads(value_json)

        self._set_hot(cache_key, value_json, int(expires_at_unix))
        return parsed

    def set(self, cache_key: str, tool_name: str, value: Any, ttl_seconds: int) -> Any:
        ttl = max(1, int(ttl_seconds))
        now_unix = int(time.time())
        expires_at_unix = now_unix + ttl
        value_json = json.dumps(value, ensure_ascii=False, separators=(",", ":"))

        pool = _get_shared_pool(self._dsn)
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO tool_cache (cache_key, tool_name, value_json, created_at, expires_at)
                VALUES (%s, %s, %s::jsonb, NOW(), NOW() + make_interval(secs => %s))
                ON CONFLICT (cache_key) DO UPDATE
                    SET tool_name  = EXCLUDED.tool_name,
                        value_json = EXCLUDED.value_json,
                        created_at = NOW(),
                        expires_at = EXCLUDED.expires_at
                """,
                (cache_key, tool_name, value_json, ttl),
            )

        self._set_hot(cache_key, value_json, expires_at_unix)
        return value

    # ------------------------------------------------------------------
    # Maintenance helpers (used by the background vacuum task)
    # ------------------------------------------------------------------

    @staticmethod
    def vacuum_expired(dsn: str | None = None) -> int:
        """Delete expired rows. Returns the number of rows removed.

        Intended to be run from a periodic task (e.g. every hour). Safe to
        call concurrently from multiple pods because it is a single
        ``DELETE`` statement; Postgres takes care of row-level locking.
        """
        resolved = dsn or _resolve_dsn()
        pool = _get_shared_pool(resolved)
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM tool_cache WHERE expires_at <= NOW()")
            deleted = cur.rowcount or 0
        if deleted:
            logger.info("tool_cache: vacuumed %d expired rows", deleted)
        return deleted
