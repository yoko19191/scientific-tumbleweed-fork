"""LangGraph Store-backed RunStore."""

from __future__ import annotations

import json
from typing import Any

from langgraph.store.base import BaseStore

from deerflow.runtime.runs.store.base import RunStore
from deerflow.utils.time import now_iso

RUNS_NS: tuple[str, ...] = ("runs",)


def _safe_json(value: Any) -> Any:
    """Return a JSON-compatible value for Store backends."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _safe_json(val) for key, val in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_safe_json(item) for item in value]
    if hasattr(value, "model_dump"):
        try:
            return _safe_json(value.model_dump())
        except Exception:
            pass
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        return str(value)


class LangGraphRunStore(RunStore):
    """Persist run metadata in the existing LangGraph Store namespace."""

    def __init__(self, store: BaseStore, *, namespace: tuple[str, ...] = RUNS_NS) -> None:
        self._store = store
        self._ns = namespace

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
        row = {
            "run_id": run_id,
            "thread_id": thread_id,
            "assistant_id": assistant_id,
            "user_id": user_id,
            "status": status,
            "on_disconnect": on_disconnect,
            "multitask_strategy": multitask_strategy,
            "metadata": _safe_json(metadata) or {},
            "kwargs": _safe_json(kwargs) or {},
            "error": error,
            "model_name": model_name,
            "created_at": created_at or now,
            "updated_at": now,
        }
        await self._store.aput(self._ns, run_id, row)

    async def get(self, run_id: str, *, user_id: str | None = None) -> dict[str, Any] | None:
        item = await self._store.aget(self._ns, run_id)
        if item is None:
            return None
        row = dict(item.value)
        if user_id is not None and row.get("user_id") != user_id:
            return None
        return row

    async def list_by_thread(
        self,
        thread_id: str,
        *,
        user_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        items = await self._store.asearch(self._ns, limit=10_000)
        rows = [
            dict(item.value)
            for item in items
            if item.value.get("thread_id") == thread_id and (user_id is None or item.value.get("user_id") == user_id)
        ]
        rows.sort(key=lambda row: row.get("created_at") or "", reverse=True)
        return rows[:limit]

    async def update_status(self, run_id: str, status: str, *, error: str | None = None) -> None:
        row = await self.get(run_id)
        if row is None:
            return
        row["status"] = status
        if error is not None:
            row["error"] = error
        row["updated_at"] = now_iso()
        await self._store.aput(self._ns, run_id, row)

    async def update_model_name(self, run_id: str, model_name: str | None) -> None:
        row = await self.get(run_id)
        if row is None:
            return
        row["model_name"] = model_name
        row["updated_at"] = now_iso()
        await self._store.aput(self._ns, run_id, row)

    async def delete(self, run_id: str) -> None:
        await self._store.adelete(self._ns, run_id)
