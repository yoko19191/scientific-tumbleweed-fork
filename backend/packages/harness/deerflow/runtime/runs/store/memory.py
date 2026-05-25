"""In-memory RunStore for tests and memory-only runtime setups."""

from __future__ import annotations

from typing import Any

from deerflow.runtime.runs.store.base import RunStore
from deerflow.utils.time import now_iso


class MemoryRunStore(RunStore):
    """Simple dict-backed RunStore."""

    def __init__(self) -> None:
        self._runs: dict[str, dict[str, Any]] = {}

    async def put(
        self,
        run_id: str,
        *,
        thread_id: str,
        assistant_id: str | None = None,
        user_id: str | None = None,
        status: str = "pending",
        on_disconnect: str = "cancel",
        multitask_strategy: str = "reject",
        metadata: dict[str, Any] | None = None,
        kwargs: dict[str, Any] | None = None,
        error: str | None = None,
        model_name: str | None = None,
        created_at: str | None = None,
    ) -> None:
        now = now_iso()
        self._runs[run_id] = {
            "run_id": run_id,
            "thread_id": thread_id,
            "assistant_id": assistant_id,
            "user_id": user_id,
            "status": status,
            "on_disconnect": on_disconnect,
            "multitask_strategy": multitask_strategy,
            "metadata": metadata or {},
            "kwargs": kwargs or {},
            "error": error,
            "model_name": model_name,
            "created_at": created_at or now,
            "updated_at": now,
        }

    async def get(self, run_id: str, *, user_id: str | None = None) -> dict[str, Any] | None:
        row = self._runs.get(run_id)
        if row is None:
            return None
        if user_id is not None and row.get("user_id") != user_id:
            return None
        return dict(row)

    async def list_by_thread(
        self,
        thread_id: str,
        *,
        user_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        rows = [
            dict(row)
            for row in self._runs.values()
            if row.get("thread_id") == thread_id and (user_id is None or row.get("user_id") == user_id)
        ]
        rows.sort(key=lambda row: row.get("created_at") or "", reverse=True)
        return rows[:limit]

    async def update_status(self, run_id: str, status: str, *, error: str | None = None) -> None:
        row = self._runs.get(run_id)
        if row is None:
            return
        row["status"] = status
        if error is not None:
            row["error"] = error
        row["updated_at"] = now_iso()

    async def update_model_name(self, run_id: str, model_name: str | None) -> None:
        row = self._runs.get(run_id)
        if row is None:
            return
        row["model_name"] = model_name
        row["updated_at"] = now_iso()

    async def delete(self, run_id: str) -> None:
        self._runs.pop(run_id, None)
