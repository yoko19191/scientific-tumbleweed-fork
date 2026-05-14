from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Protocol

from deerflow.runtime.store._sqlite_utils import ensure_sqlite_parent_dir, resolve_sqlite_conn_str

logger = logging.getLogger(__name__)

_CACHE_SCHEMA_VERSION = "v1"
_CACHE_INSTANCES: dict[tuple[str, int], "TTLCache"] = {}
_CACHE_INSTANCES_LOCK = threading.Lock()


class TTLCache(Protocol):
    """Common interface for the sqlite/postgres TTL caches.

    Kept minimal — just what ``tools.py`` callers use.
    """

    @property
    def db_path(self) -> str: ...

    def get(self, cache_key: str) -> Any | None: ...

    def set(self, cache_key: str, tool_name: str, value: Any, ttl_seconds: int) -> Any: ...


def _normalize_for_cache(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _normalize_for_cache(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_normalize_for_cache(item) for item in value]
    return value


def build_cache_key(tool_name: str, endpoint: str, params: dict[str, Any], requested_fields: list[str]) -> str:
    payload = {
        "schema_version": _CACHE_SCHEMA_VERSION,
        "tool_name": tool_name,
        "endpoint": endpoint,
        "params": _normalize_for_cache(params),
        "requested_fields": requested_fields,
    }
    normalized = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256(normalized.encode("utf-8")).hexdigest()


@dataclass(slots=True)
class CacheEntry:
    value_json: str
    expires_at: int


class SQLiteTTLCache:
    def __init__(self, db_path: str, hot_max_entries: int = 256) -> None:
        self._db_path = resolve_sqlite_conn_str(db_path)
        self._hot_max_entries = max(1, hot_max_entries)
        self._hot_cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.Lock()
        ensure_sqlite_parent_dir(self._db_path)
        self._initialize_db()

    @property
    def db_path(self) -> str:
        return self._db_path

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cache_entries (
                    cache_key TEXT PRIMARY KEY,
                    tool_name TEXT NOT NULL,
                    value_json TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    expires_at INTEGER NOT NULL
                )
                """
            )
            conn.commit()

    def _get_hot(self, cache_key: str) -> Any | None:
        now = int(time.time())
        with self._lock:
            entry = self._hot_cache.get(cache_key)
            if entry is None:
                return None
            if entry.expires_at <= now:
                self._hot_cache.pop(cache_key, None)
                return None
            self._hot_cache.move_to_end(cache_key)
            return json.loads(entry.value_json)

    def _set_hot(self, cache_key: str, value_json: str, expires_at: int) -> None:
        with self._lock:
            self._hot_cache[cache_key] = CacheEntry(value_json=value_json, expires_at=expires_at)
            self._hot_cache.move_to_end(cache_key)
            while len(self._hot_cache) > self._hot_max_entries:
                self._hot_cache.popitem(last=False)

    def get(self, cache_key: str) -> Any | None:
        hot = self._get_hot(cache_key)
        if hot is not None:
            return hot

        now = int(time.time())
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value_json, expires_at FROM cache_entries WHERE cache_key = ?",
                (cache_key,),
            ).fetchone()
            if row is None:
                return None
            if int(row["expires_at"]) <= now:
                conn.execute("DELETE FROM cache_entries WHERE cache_key = ?", (cache_key,))
                conn.commit()
                return None
            value_json = str(row["value_json"])
            expires_at = int(row["expires_at"])

        self._set_hot(cache_key, value_json, expires_at)
        return json.loads(value_json)

    def set(self, cache_key: str, tool_name: str, value: Any, ttl_seconds: int) -> Any:
        now = int(time.time())
        ttl = max(1, ttl_seconds)
        expires_at = now + ttl
        value_json = json.dumps(value, ensure_ascii=False, separators=(",", ":"))

        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO cache_entries (
                    cache_key, tool_name, value_json, created_at, expires_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (cache_key, tool_name, value_json, now, expires_at),
            )
            conn.commit()

        self._set_hot(cache_key, value_json, expires_at)
        return value


def get_sqlite_ttl_cache(db_path: str, hot_max_entries: int = 256) -> TTLCache:
    """Return the TTL cache backing the given ``db_path``.

    Historically this returned a :class:`SQLiteTTLCache`; after the
    Postgres migration the production backend is :class:`PostgresTTLCache`,
    sharing the module-level sync SQLAlchemy engine. If the engine is not
    initialised (offline tests, ad-hoc CLI usage) the function transparently
    falls back to the legacy :class:`SQLiteTTLCache` at ``db_path`` so the
    test suite and tooling-without-DB paths keep working.

    The function name is preserved for backward compatibility; the return
    type is the shared :class:`TTLCache` protocol.
    """
    try:
        from deerflow.community.semantic_scholar.postgres_cache import (
            PostgresTTLCache,
        )
        from deerflow.db import get_sync_engine

        # Raises if the sync engine is not initialised — we fall through to
        # the SQLite fallback in that case.
        engine_url = str(get_sync_engine().url)
        key = (f"postgres::{engine_url}", max(1, hot_max_entries))
        with _CACHE_INSTANCES_LOCK:
            cache = _CACHE_INSTANCES.get(key)
            if cache is None:
                cache = PostgresTTLCache(hot_max_entries=hot_max_entries)
                _CACHE_INSTANCES[key] = cache
            return cache
    except Exception as exc:
        logger.warning(
            "PostgresTTLCache unavailable (%s); falling back to SQLite at %s",
            exc,
            db_path,
        )

    resolved = resolve_sqlite_conn_str(db_path)
    key = (resolved, max(1, hot_max_entries))
    with _CACHE_INSTANCES_LOCK:
        cache = _CACHE_INSTANCES.get(key)
        if cache is None:
            cache = SQLiteTTLCache(db_path=resolved, hot_max_entries=hot_max_entries)
            _CACHE_INSTANCES[key] = cache
        return cache


# Preferred public name for new callers.
get_tool_cache = get_sqlite_ttl_cache
