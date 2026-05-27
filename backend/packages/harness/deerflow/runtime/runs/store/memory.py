"""In-memory RunStore for tests and memory-only runtime setups."""

from __future__ import annotations

from typing import Any

from deerflow.runtime.runs.store.base import RunStore
from deerflow.utils.time import now_iso

_MAX_MODEL_NAME_LEN = 128


def _normalize_model_name(model_name: str | None) -> str | None:
    if model_name is None:
        return None
    if not isinstance(model_name, str):
        model_name = str(model_name)
    normalized = model_name.strip()
    return normalized[:_MAX_MODEL_NAME_LEN] if normalized else None


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
        row["model_name"] = _normalize_model_name(model_name)
        row["updated_at"] = now_iso()

    async def update_run_completion(self, run_id: str, **kwargs: Any) -> None:
        await self._update_run_summary(run_id, **kwargs)

    async def update_run_progress(self, run_id: str, **kwargs: Any) -> None:
        row = self._runs.get(run_id)
        if row is None or row.get("status") != "running":
            return
        await self._update_run_summary(run_id, **kwargs)

    async def _update_run_summary(self, run_id: str, **kwargs: Any) -> None:
        row = self._runs.get(run_id)
        if row is None:
            return
        for key, value in kwargs.items():
            if value is not None:
                row[key] = value
        row["updated_at"] = now_iso()

    async def aggregate_tokens_by_thread(self, thread_id: str, *, include_active: bool = False) -> dict[str, Any]:
        rows = [
            row
            for row in self._runs.values()
            if row.get("thread_id") == thread_id and (include_active or row.get("status") not in {"pending", "running"})
        ]
        return _aggregate_token_rows(rows)

    async def delete(self, run_id: str) -> None:
        self._runs.pop(run_id, None)


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
