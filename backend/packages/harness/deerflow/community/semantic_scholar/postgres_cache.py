"""PostgreSQL-backed TTL cache (SQLModel sync session).

Drop-in replacement for :class:`SQLiteTTLCache` backed by the shared
``tool_cache`` table. Exposes the same ``get`` / ``set`` / ``db_path``
surface so callers in ``community/semantic_scholar/tools.py`` and
``community/academic_search/tools.py`` do not need to change.

Design notes
------------
- Uses the module-level sync SQLAlchemy engine from
  :mod:`deerflow.db.engine`. All Postgres-backed synchronous repositories
  share one engine + one connection pool instead of maintaining their
  own per-module ``psycopg_pool.ConnectionPool`` instances.
- Keeps the same in-process "hot cache" (bounded LRU) as the SQLite
  version — cache lookups are the main hit path and should not require a
  Postgres round-trip.
- TTL is represented as ``expires_at timestamptz``; reads filter with
  ``expires_at > NOW()`` so expired rows are never returned, and a
  background vacuum task periodically deletes them.
- ``INSERT … ON CONFLICT DO UPDATE`` provides the same semantics as
  sqlite's ``INSERT OR REPLACE``.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import delete, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlmodel import select

from deerflow.db.models.tool_cache import ToolCacheEntry

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class _HotCacheEntry:
    value_json: str
    expires_at_unix: int


class PostgresTTLCache:
    """TTL cache stored in the ``tool_cache`` Postgres table.

    Exposes the same ``get`` / ``set`` / ``db_path`` surface as the
    legacy :class:`SQLiteTTLCache` so existing callers compile unchanged.
    """

    def __init__(self, hot_max_entries: int = 256) -> None:
        self._hot_max_entries = max(1, hot_max_entries)
        self._hot_cache: OrderedDict[str, _HotCacheEntry] = OrderedDict()
        self._lock = threading.Lock()

    @property
    def db_path(self) -> str:
        """Best-effort identifier for diagnostics. Returns the bound engine URL."""
        try:
            from deerflow.db import get_sync_engine

            return str(get_sync_engine().url)
        except Exception:
            return "postgres://tool_cache"

    # ------------------------------------------------------------------
    # Hot-cache helpers (identical semantics to SQLiteTTLCache)
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

        from deerflow.db import sync_session_scope

        with sync_session_scope() as session:
            now = datetime.now(timezone.utc)
            row = session.exec(
                select(ToolCacheEntry).where(
                    ToolCacheEntry.cache_key == cache_key,
                    ToolCacheEntry.expires_at > now,
                )
            ).first()

        if row is None:
            return None

        value = row.value_json
        if isinstance(value, (dict, list)):
            value_json = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
            parsed: Any = value
        else:
            value_json = str(value)
            parsed = json.loads(value_json)

        self._set_hot(cache_key, value_json, int(row.expires_at.timestamp()))
        return parsed

    def set(self, cache_key: str, tool_name: str, value: Any, ttl_seconds: int) -> Any:
        ttl = max(1, int(ttl_seconds))
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=ttl)
        value_json = json.dumps(value, ensure_ascii=False, separators=(",", ":"))

        from deerflow.db import sync_session_scope

        with sync_session_scope() as session:
            stmt = (
                pg_insert(ToolCacheEntry)
                .values(
                    cache_key=cache_key,
                    tool_name=tool_name,
                    value_json=value,
                    created_at=now,
                    expires_at=expires_at,
                )
                .on_conflict_do_update(
                    index_elements=[ToolCacheEntry.cache_key],
                    set_=dict(
                        tool_name=tool_name,
                        value_json=value,
                        created_at=now,
                        expires_at=expires_at,
                    ),
                )
            )
            session.execute(stmt)

        self._set_hot(cache_key, value_json, int(expires_at.timestamp()))
        return value

    # ------------------------------------------------------------------
    # Maintenance helpers (used by the background vacuum task)
    # ------------------------------------------------------------------

    @staticmethod
    def vacuum_expired() -> int:
        """Delete expired rows. Returns the number of rows removed.

        Intended to be run from a periodic task (e.g. every hour). Safe to
        call concurrently from multiple pods — it is a single ``DELETE``
        statement and Postgres handles row-level locking.
        """
        from deerflow.db import sync_session_scope

        with sync_session_scope() as session:
            result = session.execute(
                delete(ToolCacheEntry).where(
                    ToolCacheEntry.expires_at <= text("NOW()")
                )
            )
            deleted = int(result.rowcount or 0)

        if deleted:
            logger.info("tool_cache: vacuumed %d expired rows", deleted)
        return deleted
