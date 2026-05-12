"""PostgreSQL-backed memory storage (SQLModel sync session).

Replaces the file-based :class:`FileMemoryStorage` that writes
``.deer-flow/memory.json`` and ``.deer-flow/users/{user_id}/memory.json``.

Design notes
------------
- ``MemoryStorage`` is synchronous (called from both sync prompt-generation
  paths and async FastAPI routers via the thread pool), so this backend
  uses the module-level sync SQLAlchemy engine from
  :mod:`deerflow.db.engine`.
- Global memory (no ``user_id``) lands under the sentinel
  ``user_id = '__global__'`` so the primary key stays NOT NULL and the
  query path is uniform.
- Upserts go through PostgreSQL's ``INSERT … ON CONFLICT DO UPDATE`` with
  a ``version`` column bump, matching the optimistic-locking pattern
  LangGraph's own store uses. Last-writer-wins is intentional.
- An in-process cache mirrors the legacy ``FileMemoryStorage`` behaviour:
  ``load()`` is hot on the prompt-generation path and we don't want every
  call to round-trip Postgres.
"""

from __future__ import annotations

import logging
import threading
from typing import Any

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlmodel import select

from deerflow.agents.memory.storage import (
    MemoryStorage,
    create_empty_memory,
    utc_now_iso_z,
)
from deerflow.db.models.user_memory import UserMemory

logger = logging.getLogger(__name__)

_GLOBAL_USER_ID = "__global__"


class PostgresMemoryStorage(MemoryStorage):
    """Store memory as JSONB rows in the ``user_memory`` table."""

    def __init__(self) -> None:
        # Cache: scope key -> (memory_data, version). Invalidated on save.
        self._cache: dict[str, tuple[dict[str, Any], int]] = {}
        self._cache_lock = threading.Lock()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

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
        return self._fetch_and_cache(self._scope_key(user_id))

    def _fetch_and_cache(self, key: str) -> dict[str, Any]:
        from deerflow.db import sync_session_scope

        with sync_session_scope() as session:
            row = session.exec(
                select(UserMemory).where(UserMemory.user_id == key)
            ).first()

        if row is None:
            data = create_empty_memory()
            version = 0
        else:
            data = dict(row.data) if isinstance(row.data, dict) else row.data
            version = int(row.version)

        with self._cache_lock:
            self._cache[key] = (data, version)
        return data

    def save(self, memory_data: dict[str, Any], user_id: str | None = None) -> bool:
        """Persist memory to Postgres and refresh the cache."""
        key = self._scope_key(user_id)

        # Mirror FileMemoryStorage: stamp lastUpdated without mutating the
        # caller's dict; only update the cache after the DB write succeeds.
        stamped = {**memory_data, "lastUpdated": utc_now_iso_z()}

        try:
            from deerflow.db import sync_session_scope

            with sync_session_scope() as session:
                stmt = (
                    pg_insert(UserMemory)
                    .values(user_id=key, data=stamped, version=1)
                    .on_conflict_do_update(
                        index_elements=[UserMemory.user_id],
                        set_=dict(
                            data=stamped,
                            version=UserMemory.version + 1,
                        ),
                    )
                    .returning(UserMemory.version)
                )
                result = session.execute(stmt)
                new_version = int(result.scalar_one())
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
        """No per-instance resources to release; cache clears itself."""
        with self._cache_lock:
            self._cache.clear()
