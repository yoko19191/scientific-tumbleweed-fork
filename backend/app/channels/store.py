"""ChannelStore — persists IM chat-to-Scientific Tumbleweed thread mappings.

Backends
--------
- :class:`PostgresChannelStore` (default): rows live in the
  ``channel_threads`` Postgres table accessed through SQLModel /
  SQLAlchemy. Shared across gateway replicas.
- :class:`FileChannelStore` (fallback): the legacy JSON-file store, kept
  as a testing convenience and an offline-mode fallback when no Postgres
  engine is available.

Selection
---------
:class:`ChannelStore` is a factory function that returns the configured
backend. Tests and call sites that still pass ``path=...`` get a
:class:`FileChannelStore` instance transparently — this preserves the
old signature exactly.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import delete, or_, select

from deerflow.db.models.channel_thread import ChannelThread as ChannelThreadRow

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
# Postgres backend (SQLModel sync session)
# ---------------------------------------------------------------------------


class PostgresChannelStore(_BaseChannelStore):
    """PostgreSQL-backed channel thread store.

    Schema is created by :func:`deerflow.db.setup.ensure_schema` at gateway
    startup — this class assumes the ``channel_threads`` table exists. All
    DB access goes through the shared sync SQLAlchemy engine in
    :mod:`deerflow.db`.
    """

    def __init__(self) -> None:
        # Trigger early failure if the engine isn't initialised; that lets
        # the factory function fall through to ``FileChannelStore``.
        from deerflow.db import get_sync_engine

        get_sync_engine()

    # -- public API --------------------------------------------------------

    def get_thread_id(self, channel_name: str, chat_id: str, topic_id: str | None = None) -> str | None:
        from deerflow.db import sync_session_scope

        key = self._key(channel_name, chat_id, topic_id)
        with sync_session_scope() as session:
            row = session.execute(
                select(ChannelThreadRow.thread_id).where(ChannelThreadRow.key == key)
            ).scalar_one_or_none()
        return str(row) if row else None

    def set_thread_id(
        self,
        channel_name: str,
        chat_id: str,
        thread_id: str,
        *,
        topic_id: str | None = None,
        user_id: str = "",
    ) -> None:
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        from deerflow.db import sync_session_scope

        key = self._key(channel_name, chat_id, topic_id)
        now = datetime.now(timezone.utc)

        with sync_session_scope() as session:
            stmt = (
                pg_insert(ChannelThreadRow)
                .values(
                    key=key,
                    thread_id=thread_id,
                    user_id=user_id,
                    created_at=now,
                    updated_at=now,
                )
                .on_conflict_do_update(
                    index_elements=[ChannelThreadRow.key],
                    set_=dict(
                        thread_id=thread_id,
                        user_id=user_id,
                        updated_at=now,
                    ),
                )
            )
            session.execute(stmt)

    def remove(self, channel_name: str, chat_id: str, topic_id: str | None = None) -> bool:
        from deerflow.db import sync_session_scope

        with sync_session_scope() as session:
            if topic_id is not None:
                key = self._key(channel_name, chat_id, topic_id)
                result = session.execute(
                    delete(ChannelThreadRow).where(ChannelThreadRow.key == key)
                )
                return (result.rowcount or 0) > 0

            base_key = self._key(channel_name, chat_id)
            prefix = base_key + ":"
            result = session.execute(
                delete(ChannelThreadRow).where(
                    or_(
                        ChannelThreadRow.key == base_key,
                        ChannelThreadRow.key.like(prefix + "%"),
                    )
                )
            )
            return (result.rowcount or 0) > 0

    def list_entries(self, channel_name: str | None = None) -> list[dict[str, Any]]:
        from deerflow.db import sync_session_scope

        with sync_session_scope() as session:
            rows = session.execute(select(ChannelThreadRow)).scalars().all()

        results: list[dict[str, Any]] = []
        for row in rows:
            parts = row.key.split(":", 2)
            ch = parts[0]
            chat = parts[1] if len(parts) > 1 else ""
            topic = parts[2] if len(parts) > 2 else None
            if channel_name and ch != channel_name:
                continue
            item: dict[str, Any] = {
                "channel_name": ch,
                "chat_id": chat,
                "thread_id": row.thread_id,
                "user_id": row.user_id or "",
                "created_at": row.created_at.timestamp() if row.created_at else 0.0,
                "updated_at": row.updated_at.timestamp() if row.updated_at else 0.0,
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
    - Otherwise, prefer :class:`PostgresChannelStore` when the sync DB
      engine is initialised; fall back to :class:`FileChannelStore` on
      failure (engine not initialised, DB unreachable, etc).
    - Set ``DEERFLOW_CHANNEL_STORE_BACKEND=file`` to force the file backend
      regardless of DB availability (useful for single-file deployments).
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

