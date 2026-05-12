"""ChannelStore — persists IM chat-to-Scientific Tumbleweed thread mappings.

Backends
--------
- :class:`PostgresChannelStore` (default): rows live in the ``channel_threads``
  Postgres table. Shared across gateway replicas.
- :class:`FileChannelStore` (fallback): the legacy JSON-file store, kept as a
  testing convenience and an offline-mode fallback when no Postgres DSN is
  available.

Selection
---------
:class:`ChannelStore` is a factory function that returns the configured
backend. Tests and call sites that still pass ``path=...`` get a
:class:`FileChannelStore` instance transparently — this preserves the old
signature exactly.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from psycopg_pool import ConnectionPool

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------


class _BaseChannelStore(ABC):
    """Common API for all channel stores."""

    @staticmethod
    def _key(channel_name: str, chat_id: str, topic_id: str | None = None) -> str:
        if topic_id:
            return f"{channel_name}:{chat_id}:{topic_id}"
        return f"{channel_name}:{chat_id}"

    @abstractmethod
    def get_thread_id(
        self, channel_name: str, chat_id: str, topic_id: str | None = None
    ) -> str | None: ...

    @abstractmethod
    def set_thread_id(
        self,
        channel_name: str,
        chat_id: str,
        thread_id: str,
        *,
        topic_id: str | None = None,
        user_id: str = "",
    ) -> None: ...

    @abstractmethod
    def remove(
        self, channel_name: str, chat_id: str, topic_id: str | None = None
    ) -> bool: ...

    @abstractmethod
    def list_entries(self, channel_name: str | None = None) -> list[dict[str, Any]]: ...


# ---------------------------------------------------------------------------
# File backend (legacy JSON)
# ---------------------------------------------------------------------------


class FileChannelStore(_BaseChannelStore):
    """JSON-file-backed store that maps IM conversations to Scientific Tumbleweed threads.

    Data layout (on disk)::

        {
            "<channel_name>:<chat_id>": {
                "thread_id": "<uuid>",
                "user_id": "<platform_user>",
                "created_at": 1700000000.0,
                "updated_at": 1700000000.0
            },
            ...
        }

    The store is intentionally simple — a single JSON file that is atomically
    rewritten on every mutation.
    """

    def __init__(self, path: str | Path | None = None) -> None:
        if path is None:
            from deerflow.config.paths import get_paths

            path = Path(get_paths().base_dir) / "channels" / "store.json"
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._data: dict[str, dict[str, Any]] = self._load()
        self._lock = threading.Lock()

    # -- persistence -------------------------------------------------------

    def _load(self) -> dict[str, dict[str, Any]]:
        if self._path.exists():
            try:
                return json.loads(self._path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                logger.warning("Corrupt channel store at %s, starting fresh", self._path)
        return {}

    def _save(self) -> None:
        fd = tempfile.NamedTemporaryFile(
            mode="w",
            dir=self._path.parent,
            suffix=".tmp",
            delete=False,
        )
        try:
            json.dump(self._data, fd, indent=2)
            fd.close()
            Path(fd.name).replace(self._path)
        except BaseException:
            fd.close()
            Path(fd.name).unlink(missing_ok=True)
            raise

    # -- public API --------------------------------------------------------

    def get_thread_id(self, channel_name: str, chat_id: str, topic_id: str | None = None) -> str | None:
        entry = self._data.get(self._key(channel_name, chat_id, topic_id))
        return entry["thread_id"] if entry else None

    def set_thread_id(
        self,
        channel_name: str,
        chat_id: str,
        thread_id: str,
        *,
        topic_id: str | None = None,
        user_id: str = "",
    ) -> None:
        with self._lock:
            key = self._key(channel_name, chat_id, topic_id)
            now = time.time()
            existing = self._data.get(key)
            self._data[key] = {
                "thread_id": thread_id,
                "user_id": user_id,
                "created_at": existing["created_at"] if existing else now,
                "updated_at": now,
            }
            self._save()

    def remove(self, channel_name: str, chat_id: str, topic_id: str | None = None) -> bool:
        with self._lock:
            if topic_id is not None:
                key = self._key(channel_name, chat_id, topic_id)
                if key in self._data:
                    del self._data[key]
                    self._save()
                    return True
                return False

            prefix = self._key(channel_name, chat_id)
            keys_to_delete = [k for k in self._data if k == prefix or k.startswith(prefix + ":")]
            if not keys_to_delete:
                return False

            for k in keys_to_delete:
                del self._data[k]
            self._save()
            return True

    def list_entries(self, channel_name: str | None = None) -> list[dict[str, Any]]:
        results = []
        for key, entry in self._data.items():
            parts = key.split(":", 2)
            ch = parts[0]
            chat = parts[1] if len(parts) > 1 else ""
            topic = parts[2] if len(parts) > 2 else None
            if channel_name and ch != channel_name:
                continue
            item: dict[str, Any] = {"channel_name": ch, "chat_id": chat, **entry}
            if topic is not None:
                item["topic_id"] = topic
            results.append(item)
        return results


# ---------------------------------------------------------------------------
# Postgres backend
# ---------------------------------------------------------------------------


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

    raise RuntimeError("POSTGRES_DSN is not configured.")


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


class PostgresChannelStore(_BaseChannelStore):
    """PostgreSQL-backed channel thread store.

    Schema is created by :func:`deerflow.db.setup.ensure_schema` at gateway
    startup — this class assumes the ``channel_threads`` table exists.
    """

    def __init__(self, dsn: str | None = None) -> None:
        self._dsn = dsn or _resolve_dsn()

    def _pool(self) -> ConnectionPool:
        return _get_shared_pool(self._dsn)

    # -- public API --------------------------------------------------------

    def get_thread_id(self, channel_name: str, chat_id: str, topic_id: str | None = None) -> str | None:
        with self._pool().connection() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT thread_id FROM channel_threads WHERE key = %s",
                (self._key(channel_name, chat_id, topic_id),),
            )
            row = cur.fetchone()
        return str(row[0]) if row else None

    def set_thread_id(
        self,
        channel_name: str,
        chat_id: str,
        thread_id: str,
        *,
        topic_id: str | None = None,
        user_id: str = "",
    ) -> None:
        key = self._key(channel_name, chat_id, topic_id)
        with self._pool().connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO channel_threads (key, thread_id, user_id)
                VALUES (%s, %s, %s)
                ON CONFLICT (key) DO UPDATE
                    SET thread_id = EXCLUDED.thread_id,
                        user_id   = EXCLUDED.user_id,
                        updated_at = NOW()
                """,
                (key, thread_id, user_id),
            )

    def remove(self, channel_name: str, chat_id: str, topic_id: str | None = None) -> bool:
        with self._pool().connection() as conn, conn.cursor() as cur:
            if topic_id is not None:
                cur.execute(
                    "DELETE FROM channel_threads WHERE key = %s",
                    (self._key(channel_name, chat_id, topic_id),),
                )
                return (cur.rowcount or 0) > 0

            # Delete the base mapping and any topic-specific children.
            base_key = self._key(channel_name, chat_id)
            prefix = base_key + ":"
            cur.execute(
                "DELETE FROM channel_threads WHERE key = %s OR key LIKE %s",
                (base_key, prefix + "%"),
            )
            return (cur.rowcount or 0) > 0

    def list_entries(self, channel_name: str | None = None) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        with self._pool().connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT key,
                       thread_id,
                       user_id,
                       EXTRACT(EPOCH FROM created_at)::double precision AS created_at,
                       EXTRACT(EPOCH FROM updated_at)::double precision AS updated_at
                  FROM channel_threads
                """
            )
            rows = cur.fetchall()

        for row in rows:
            key, thread_id, user_id, created_at, updated_at = row
            parts = str(key).split(":", 2)
            ch = parts[0]
            chat = parts[1] if len(parts) > 1 else ""
            topic = parts[2] if len(parts) > 2 else None
            if channel_name and ch != channel_name:
                continue
            item: dict[str, Any] = {
                "channel_name": ch,
                "chat_id": chat,
                "thread_id": str(thread_id),
                "user_id": user_id or "",
                "created_at": float(created_at) if created_at is not None else 0.0,
                "updated_at": float(updated_at) if updated_at is not None else 0.0,
            }
            if topic is not None:
                item["topic_id"] = topic
            results.append(item)
        return results


# ---------------------------------------------------------------------------
# Factory — chooses backend based on arguments and environment.
# ---------------------------------------------------------------------------


def ChannelStore(path: str | Path | None = None) -> _BaseChannelStore:  # noqa: N802
    """Return the configured channel store.

    - When ``path`` is provided, always returns a :class:`FileChannelStore`
      targeting that path. Used by tests and explicit file-backed callers.
    - Otherwise, prefer :class:`PostgresChannelStore` when a DSN is
      resolvable; fall back to :class:`FileChannelStore` on failure.
    - Set ``DEERFLOW_CHANNEL_STORE_BACKEND=file`` to force the file backend
      regardless of DSN availability (useful for single-file deployments).
    """
    if path is not None:
        return FileChannelStore(path=path)

    override = os.getenv("DEERFLOW_CHANNEL_STORE_BACKEND", "").strip().lower()
    if override == "file":
        return FileChannelStore()

    try:
        return PostgresChannelStore()
    except Exception as exc:
        logger.warning(
            "PostgresChannelStore unavailable (%s); falling back to FileChannelStore", exc
        )
        return FileChannelStore()
