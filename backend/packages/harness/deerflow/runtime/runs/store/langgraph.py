"""LangGraph Store-backed RunStore."""

from __future__ import annotations

import json
from typing import Any

from langgraph.store.base import BaseStore

from deerflow.runtime.runs.store.base import RunStore
from deerflow.utils.time import now_iso

RUNS_NS: tuple[str, ...] = ("runs",)
_MAX_MODEL_NAME_LEN = 128


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


def _normalize_model_name(model_name: str | None) -> str | None:
    if model_name is None:
        return None
    if not isinstance(model_name, str):
        model_name = str(model_name)
    normalized = model_name.strip()
    return normalized[:_MAX_MODEL_NAME_LEN] if normalized else None


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
        total_input_tokens: int = 0,
        total_output_tokens: int = 0,
        total_tokens: int = 0,
        llm_call_count: int = 0,
        lead_agent_tokens: int = 0,
        subagent_tokens: int = 0,
        middleware_tokens: int = 0,
        message_count: int = 0,
        last_ai_message: str | None = None,
        first_human_message: str | None = None,
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
            "model_name": _normalize_model_name(model_name),
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "total_tokens": total_tokens,
            "llm_call_count": llm_call_count,
            "lead_agent_tokens": lead_agent_tokens,
            "subagent_tokens": subagent_tokens,
            "middleware_tokens": middleware_tokens,
            "message_count": message_count,
            "last_ai_message": last_ai_message,
            "first_human_message": first_human_message,
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
        filters: dict[str, Any] = {"thread_id": thread_id}
        if user_id is not None:
            filters["user_id"] = user_id
        items = await self._store.asearch(self._ns, filter=filters, limit=10_000)
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
        row["model_name"] = _normalize_model_name(model_name)
        row["updated_at"] = now_iso()
        await self._store.aput(self._ns, run_id, row)

    async def update_run_completion(self, run_id: str, **kwargs: Any) -> None:
        await self._update_run_summary(run_id, **kwargs)

    async def update_run_progress(self, run_id: str, **kwargs: Any) -> None:
        row = await self.get(run_id)
        if row is None or row.get("status") != "running":
            return
        await self._update_run_summary(run_id, **kwargs)

    async def _update_run_summary(self, run_id: str, **kwargs: Any) -> None:
        row = await self.get(run_id)
        if row is None:
            return
        for key, value in kwargs.items():
            if value is not None:
                row[key] = _safe_json(value)
        row["updated_at"] = now_iso()
        await self._store.aput(self._ns, run_id, row)

    async def aggregate_tokens_by_thread(self, thread_id: str, *, include_active: bool = False) -> dict[str, Any]:
        items = await self._store.asearch(self._ns, filter={"thread_id": thread_id}, limit=10_000)
        rows = [
            dict(item.value)
            for item in items
            if item.value.get("thread_id") == thread_id and (include_active or item.value.get("status") not in {"pending", "running"})
        ]
        return _aggregate_token_rows(rows)

    async def delete(self, run_id: str) -> None:
        await self._store.adelete(self._ns, run_id)


def _aggregate_token_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_model: dict[str, dict[str, int]] = {}
    by_caller = {"lead_agent": 0, "subagent": 0, "middleware": 0}
    total_input = total_output = total = total_runs = 0
    for row in rows:
        row_total = row.get("total_tokens", 0) or 0
        if row_total <= 0:
            continue
        total_runs += 1
        total_input += row.get("total_input_tokens", 0) or 0
        total_output += row.get("total_output_tokens", 0) or 0
        total += row_total
        model = row.get("model_name") or "unknown"
        model_bucket = by_model.setdefault(model, {"tokens": 0, "runs": 0})
        model_bucket["tokens"] += row_total
        model_bucket["runs"] += 1
        by_caller["lead_agent"] += row.get("lead_agent_tokens", 0) or 0
        by_caller["subagent"] += row.get("subagent_tokens", 0) or 0
        by_caller["middleware"] += row.get("middleware_tokens", 0) or 0
    return {
        "total_tokens": total,
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "total_runs": total_runs,
        "by_model": by_model,
        "by_caller": by_caller,
    }
