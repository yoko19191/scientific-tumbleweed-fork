"""In-memory run registry."""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import TYPE_CHECKING, Any

from deerflow.utils.time import now_iso as _now_iso

from .records import RunRecord
from .schemas import DisconnectMode, RunStatus

if TYPE_CHECKING:
    from deerflow.runtime.runs.store.base import RunStore

logger = logging.getLogger(__name__)


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


class RunManager:
    """In-memory run registry with optional persistent store backing."""

    def __init__(self, store: RunStore | None = None) -> None:
        self._runs: dict[str, RunRecord] = {}
        self._lock = asyncio.Lock()
        self._store = store

    async def _persist_to_store(self, record: RunRecord) -> None:
        """Best-effort persist run metadata to the backing store."""
        if self._store is None:
            return
        try:
            await self._store.put(
                record.run_id,
                thread_id=record.thread_id,
                assistant_id=record.assistant_id,
                user_id=record.metadata.get("user_id"),
                status=record.status.value,
                on_disconnect=record.on_disconnect.value,
                multitask_strategy=record.multitask_strategy,
                metadata=record.metadata or {},
                kwargs=record.kwargs or {},
                error=record.error,
                model_name=record.model_name,
                created_at=record.created_at,
                total_input_tokens=record.total_input_tokens,
                total_output_tokens=record.total_output_tokens,
                total_tokens=record.total_tokens,
                llm_call_count=record.llm_call_count,
                lead_agent_tokens=record.lead_agent_tokens,
                subagent_tokens=record.subagent_tokens,
                middleware_tokens=record.middleware_tokens,
                message_count=record.message_count,
                last_ai_message=record.last_ai_message,
                first_human_message=record.first_human_message,
            )
        except Exception:
            logger.warning("Failed to persist run %s to store", record.run_id, exc_info=True)

    async def _persist_status(self, run_id: str, status: RunStatus, *, error: str | None = None) -> None:
        """Best-effort persist a status transition to the backing store."""
        if self._store is None:
            return
        try:
            await self._store.update_status(run_id, status.value, error=error)
        except Exception:
            logger.warning("Failed to persist status update for run %s", run_id, exc_info=True)

    async def _persist_model_name(self, run_id: str, model_name: str | None) -> None:
        """Best-effort persist a model_name transition to the backing store."""
        if self._store is None:
            return
        try:
            await self._store.update_model_name(run_id, model_name)
        except Exception:
            logger.warning("Failed to persist model_name update for run %s", run_id, exc_info=True)

    @staticmethod
    def _record_from_store(row: dict[str, Any]) -> RunRecord:
        """Build a read-only runtime record from a persisted store row."""
        return RunRecord.from_store_row(row)

    async def update_run_completion(self, run_id: str, **kwargs: Any) -> None:
        """Persist token usage and completion summary to memory and store."""
        async with self._lock:
            record = self._runs.get(run_id)
            if record is not None:
                for key, value in kwargs.items():
                    if hasattr(record, key) and value is not None:
                        setattr(record, key, value)
                record.updated_at = _now_iso()
        if self._store is not None:
            try:
                await self._store.update_run_completion(run_id, **kwargs)
            except Exception:
                logger.warning("Failed to persist run completion for %s", run_id, exc_info=True)

    async def update_run_progress(self, run_id: str, **kwargs: Any) -> None:
        """Persist a running token/message snapshot without changing status."""
        should_persist = True
        async with self._lock:
            record = self._runs.get(run_id)
            if record is not None:
                should_persist = record.status == RunStatus.running
                if should_persist:
                    for key, value in kwargs.items():
                        if hasattr(record, key) and value is not None:
                            setattr(record, key, value)
                    record.updated_at = _now_iso()
        if should_persist and self._store is not None:
            try:
                await self._store.update_run_progress(run_id, **kwargs)
            except Exception:
                logger.warning("Failed to persist run progress for %s", run_id, exc_info=True)

    async def create(
        self,
        thread_id: str,
        assistant_id: str | None = None,
        *,
        on_disconnect: DisconnectMode = DisconnectMode.cancel,
        metadata: dict | None = None,
        kwargs: dict | None = None,
        multitask_strategy: str = "reject",
    ) -> RunRecord:
        """Create a new pending run and register it."""
        run_id = str(uuid.uuid4())
        now = _now_iso()
        record = RunRecord(
            run_id=run_id,
            thread_id=thread_id,
            assistant_id=assistant_id,
            status=RunStatus.pending,
            on_disconnect=on_disconnect,
            multitask_strategy=multitask_strategy,
            metadata=metadata or {},
            kwargs=kwargs or {},
            created_at=now,
            updated_at=now,
        )
        async with self._lock:
            self._runs[run_id] = record
        await self._persist_to_store(record)
        logger.info("Run created: run_id=%s thread_id=%s", run_id, thread_id)
        return record

    async def get(self, run_id: str, *, user_id: str | None = None) -> RunRecord | None:
        """Return a run record by ID, hydrating from store when needed."""
        async with self._lock:
            record = self._runs.get(run_id)
        if record is not None:
            return record
        if self._store is None:
            return None
        try:
            row = await self._store.get(run_id, user_id=user_id)
        except Exception:
            logger.warning("Failed to hydrate run %s from store", run_id, exc_info=True)
            return None
        async with self._lock:
            record = self._runs.get(run_id)
        if record is not None:
            return record
        if row is None:
            return None
        try:
            return self._record_from_store(row)
        except Exception:
            logger.warning("Failed to map store row for run %s", run_id, exc_info=True)
            return None

    async def aget(self, run_id: str, *, user_id: str | None = None) -> RunRecord | None:
        """Backward-compatible async alias for :meth:`get`."""
        return await self.get(run_id, user_id=user_id)

    async def list_by_thread(self, thread_id: str, *, user_id: str | None = None, limit: int = 100) -> list[RunRecord]:
        """Return all runs for a given thread, newest first."""
        async with self._lock:
            # Dict insertion order matches creation order, so reversing it gives
            # us deterministic newest-first results even when timestamps tie.
            memory_records = [r for r in self._runs.values() if r.thread_id == thread_id]
        sorted_memory_records = sorted(
            reversed(memory_records),
            key=lambda r: r.created_at,
            reverse=True,
        )
        if self._store is None:
            return sorted_memory_records[:limit]
        records_by_id = {record.run_id: record for record in memory_records}
        try:
            rows = await self._store.list_by_thread(thread_id, user_id=user_id, limit=limit)
        except Exception:
            logger.warning("Failed to hydrate runs for thread %s from store", thread_id, exc_info=True)
            return sorted_memory_records[:limit]
        for row in rows:
            run_id = row.get("run_id")
            if run_id and run_id not in records_by_id:
                try:
                    records_by_id[run_id] = self._record_from_store(row)
                except Exception:
                    logger.warning("Failed to map store row for run %s", run_id, exc_info=True)
        return sorted(records_by_id.values(), key=lambda record: record.created_at, reverse=True)[:limit]

    async def aggregate_tokens_by_thread(self, thread_id: str, *, include_active: bool = False) -> dict[str, Any]:
        """Aggregate token usage for a thread from the backing store when available."""
        if self._store is not None:
            try:
                return await self._store.aggregate_tokens_by_thread(thread_id, include_active=include_active)
            except Exception:
                logger.warning("Failed to aggregate token usage for thread %s from store", thread_id, exc_info=True)

        async with self._lock:
            rows = [
                {
                    "thread_id": record.thread_id,
                    "status": record.status.value,
                    "model_name": record.model_name,
                    "total_input_tokens": record.total_input_tokens,
                    "total_output_tokens": record.total_output_tokens,
                    "total_tokens": record.total_tokens,
                    "lead_agent_tokens": record.lead_agent_tokens,
                    "subagent_tokens": record.subagent_tokens,
                    "middleware_tokens": record.middleware_tokens,
                }
                for record in self._runs.values()
                if record.thread_id == thread_id and (include_active or record.status not in {RunStatus.pending, RunStatus.running})
            ]
        return _aggregate_token_rows(rows)

    async def set_status(self, run_id: str, status: RunStatus, *, error: str | None = None) -> None:
        """Transition a run to a new status."""
        async with self._lock:
            record = self._runs.get(run_id)
            if record is None:
                logger.warning("set_status called for unknown run %s", run_id)
                return
            record.status = status
            record.updated_at = _now_iso()
            if error is not None:
                record.error = error
        await self._persist_status(run_id, status, error=error)
        logger.info("Run %s -> %s", run_id, status.value)

    async def update_model_name(self, run_id: str, model_name: str | None) -> None:
        """Update the model name captured for a run."""
        async with self._lock:
            record = self._runs.get(run_id)
            if record is None:
                logger.warning("update_model_name called for unknown run %s", run_id)
                return
            record.model_name = model_name
            record.updated_at = _now_iso()
        await self._persist_model_name(run_id, model_name)
        logger.info("Run %s model_name=%s", run_id, model_name)

    async def cancel(self, run_id: str, *, action: str = "interrupt") -> bool:
        """Request cancellation of a run.

        Args:
            run_id: The run ID to cancel.
            action: "interrupt" keeps checkpoint, "rollback" reverts to pre-run state.

        Sets the abort event with the action reason and cancels the asyncio task.
        Returns ``True`` if cancellation was initiated **or** the run was already
        interrupted (idempotent — a second cancel is a no-op success).
        Returns ``False`` only when the run is unknown to this worker or has
        reached a terminal state other than interrupted (completed, failed, etc.).
        """
        async with self._lock:
            record = self._runs.get(run_id)
            if record is None:
                return False
            if record.status == RunStatus.interrupted:
                return True  # idempotent — already cancelled on this worker
            if record.status not in (RunStatus.pending, RunStatus.running):
                return False
            record.abort_action = action
            record.abort_event.set()
            if record.task is not None and not record.task.done():
                record.task.cancel()
            record.status = RunStatus.interrupted
            record.updated_at = _now_iso()
        await self._persist_status(run_id, RunStatus.interrupted)
        logger.info("Run %s cancelled (action=%s)", run_id, action)
        return True

    async def create_or_reject(
        self,
        thread_id: str,
        assistant_id: str | None = None,
        *,
        on_disconnect: DisconnectMode = DisconnectMode.cancel,
        metadata: dict | None = None,
        kwargs: dict | None = None,
        multitask_strategy: str = "reject",
        model_name: str | None = None,
    ) -> RunRecord:
        """Atomically check for inflight runs and create a new one.

        For ``reject`` strategy, raises ``ConflictError`` if thread
        already has a pending/running run.  For ``interrupt``/``rollback``,
        cancels inflight runs before creating.

        This method holds the lock across both the check and the insert,
        eliminating the TOCTOU race in separate ``has_inflight`` + ``create``.
        """
        run_id = str(uuid.uuid4())
        now = _now_iso()

        _supported_strategies = ("reject", "interrupt", "rollback")
        interrupted_run_ids: list[str] = []

        async with self._lock:
            if multitask_strategy not in _supported_strategies:
                raise UnsupportedStrategyError(f"Multitask strategy '{multitask_strategy}' is not yet supported. Supported strategies: {', '.join(_supported_strategies)}")

            inflight = [r for r in self._runs.values() if r.thread_id == thread_id and r.status in (RunStatus.pending, RunStatus.running)]

            if multitask_strategy == "reject" and inflight:
                raise ConflictError(f"Thread {thread_id} already has an active run")

            if multitask_strategy in ("interrupt", "rollback") and inflight:
                for r in inflight:
                    r.abort_action = multitask_strategy
                    r.abort_event.set()
                    if r.task is not None and not r.task.done():
                        r.task.cancel()
                    r.status = RunStatus.interrupted
                    r.updated_at = now
                    interrupted_run_ids.append(r.run_id)
                logger.info(
                    "Cancelled %d inflight run(s) on thread %s (strategy=%s)",
                    len(inflight),
                    thread_id,
                    multitask_strategy,
                )

            record = RunRecord(
                run_id=run_id,
                thread_id=thread_id,
                assistant_id=assistant_id,
                status=RunStatus.pending,
                on_disconnect=on_disconnect,
                multitask_strategy=multitask_strategy,
                metadata=metadata or {},
                kwargs=kwargs or {},
                created_at=now,
                updated_at=now,
                model_name=model_name,
            )
            self._runs[run_id] = record

        for interrupted_run_id in interrupted_run_ids:
            await self._persist_status(interrupted_run_id, RunStatus.interrupted)
        await self._persist_to_store(record)
        logger.info("Run created: run_id=%s thread_id=%s", run_id, thread_id)
        return record

    async def has_inflight(self, thread_id: str) -> bool:
        """Return ``True`` if *thread_id* has a pending or running run."""
        async with self._lock:
            return any(r.thread_id == thread_id and r.status in (RunStatus.pending, RunStatus.running) for r in self._runs.values())

    async def cleanup(self, run_id: str, *, delay: float = 300) -> None:
        """Remove a run record after an optional delay."""
        if delay > 0:
            await asyncio.sleep(delay)
        async with self._lock:
            self._runs.pop(run_id, None)
        logger.debug("Run record %s cleaned up", run_id)


class ConflictError(Exception):
    """Raised when multitask_strategy=reject and thread has inflight runs."""


class UnsupportedStrategyError(Exception):
    """Raised when a multitask_strategy value is not yet implemented."""
