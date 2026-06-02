"""Tests for RunManager."""

import re

import pytest

from deerflow.runtime import DisconnectMode, RunManager, RunRecord, RunStatus
from deerflow.runtime.runs.store import MemoryRunStore

ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")


@pytest.fixture
def manager() -> RunManager:
    return RunManager()


def test_run_record_from_store_row_maps_defaults_and_token_fields():
    """Store-row hydration should live on the RunRecord value object."""
    record = RunRecord.from_store_row(
        {
            "run_id": "run-1",
            "thread_id": "thread-1",
            "metadata": {"user_id": "user-1"},
            "kwargs": {"input": {}},
            "total_input_tokens": 2,
            "total_output_tokens": 3,
            "total_tokens": 5,
            "llm_call_count": 1,
        }
    )

    assert record.run_id == "run-1"
    assert record.thread_id == "thread-1"
    assert record.status == RunStatus.pending
    assert record.on_disconnect == DisconnectMode.cancel
    assert record.metadata == {"user_id": "user-1"}
    assert record.kwargs == {"input": {}}
    assert record.store_only is True
    assert record.total_tokens == 5
    assert record.llm_call_count == 1


@pytest.mark.anyio
async def test_create_and_get(manager: RunManager):
    """Created run should be retrievable with new fields."""
    record = await manager.create(
        "thread-1",
        "chat_lead_agent",
        metadata={"key": "val"},
        kwargs={"input": {}},
        multitask_strategy="reject",
    )
    assert record.status == RunStatus.pending
    assert record.thread_id == "thread-1"
    assert record.assistant_id == "chat_lead_agent"
    assert record.metadata == {"key": "val"}
    assert record.kwargs == {"input": {}}
    assert record.multitask_strategy == "reject"
    assert ISO_RE.match(record.created_at)
    assert ISO_RE.match(record.updated_at)

    fetched = await manager.get(record.run_id)
    assert fetched is record


@pytest.mark.anyio
async def test_status_transitions(manager: RunManager):
    """Status should transition pending -> running -> success."""
    record = await manager.create("thread-1")
    assert record.status == RunStatus.pending

    await manager.set_status(record.run_id, RunStatus.running)
    assert record.status == RunStatus.running
    assert ISO_RE.match(record.updated_at)

    await manager.set_status(record.run_id, RunStatus.success)
    assert record.status == RunStatus.success


@pytest.mark.anyio
async def test_cancel(manager: RunManager):
    """Cancel should set abort_event and transition to interrupted."""
    record = await manager.create("thread-1")
    await manager.set_status(record.run_id, RunStatus.running)

    cancelled = await manager.cancel(record.run_id)
    assert cancelled is True
    assert record.abort_event.is_set()
    assert record.status == RunStatus.interrupted


@pytest.mark.anyio
async def test_cancel_not_inflight(manager: RunManager):
    """Cancelling a completed run should return False."""
    record = await manager.create("thread-1")
    await manager.set_status(record.run_id, RunStatus.success)

    cancelled = await manager.cancel(record.run_id)
    assert cancelled is False


@pytest.mark.anyio
async def test_list_by_thread(manager: RunManager):
    """Same thread should return multiple runs, newest first."""
    r1 = await manager.create("thread-1")
    r2 = await manager.create("thread-1")
    await manager.create("thread-2")

    runs = await manager.list_by_thread("thread-1")
    assert len(runs) == 2
    assert runs[0].run_id == r2.run_id
    assert runs[1].run_id == r1.run_id


@pytest.mark.anyio
async def test_list_by_thread_is_stable_when_timestamps_tie(manager: RunManager, monkeypatch: pytest.MonkeyPatch):
    """Newest-first ordering should not depend on timestamp precision."""
    monkeypatch.setattr("deerflow.runtime.runs.manager._now_iso", lambda: "2026-01-01T00:00:00+00:00")

    r1 = await manager.create("thread-1")
    r2 = await manager.create("thread-1")

    runs = await manager.list_by_thread("thread-1")
    assert [run.run_id for run in runs] == [r2.run_id, r1.run_id]


@pytest.mark.anyio
async def test_has_inflight(manager: RunManager):
    """has_inflight should be True when a run is pending or running."""
    record = await manager.create("thread-1")
    assert await manager.has_inflight("thread-1") is True

    await manager.set_status(record.run_id, RunStatus.success)
    assert await manager.has_inflight("thread-1") is False


@pytest.mark.anyio
async def test_has_inflight_is_thread_scoped_and_terminal_statuses_clear_index(manager: RunManager):
    """Inflight checks should only consult runs for the target thread."""
    thread_1 = await manager.create("thread-1")
    thread_2 = await manager.create("thread-2")

    assert await manager.has_inflight("thread-1") is True
    assert await manager.has_inflight("thread-2") is True

    await manager.set_status(thread_1.run_id, RunStatus.success)
    assert await manager.has_inflight("thread-1") is False
    assert await manager.has_inflight("thread-2") is True

    await manager.set_status(thread_2.run_id, RunStatus.error)
    assert await manager.has_inflight("thread-2") is False


@pytest.mark.anyio
async def test_cleanup(manager: RunManager):
    """After cleanup, the run should be gone."""
    record = await manager.create("thread-1")
    run_id = record.run_id

    await manager.cleanup(run_id, delay=0)
    assert await manager.get(run_id) is None


@pytest.mark.anyio
async def test_cleanup_removes_live_record_but_preserves_store_hydration():
    """Runtime cleanup should not delete historical run rows from the store."""
    store = MemoryRunStore()
    manager = RunManager(store=store)
    record = await manager.create_or_reject("thread-1", metadata={"user_id": "user-1"})
    await manager.set_status(record.run_id, RunStatus.success)

    await manager.cleanup(record.run_id, delay=0)

    hydrated = await manager.get(record.run_id, user_id="user-1")
    runs = await manager.list_by_thread("thread-1", user_id="user-1")
    assert hydrated is not None
    assert hydrated.store_only is True
    assert [run.run_id for run in runs] == [record.run_id]
    assert runs[0].store_only is True


@pytest.mark.anyio
async def test_set_status_with_error(manager: RunManager):
    """Error message should be stored on the record."""
    record = await manager.create("thread-1")
    await manager.set_status(record.run_id, RunStatus.error, error="Something went wrong")
    assert record.status == RunStatus.error
    assert record.error == "Something went wrong"


@pytest.mark.anyio
async def test_get_nonexistent(manager: RunManager):
    """Getting a nonexistent run should return None."""
    assert await manager.get("does-not-exist") is None


@pytest.mark.anyio
async def test_create_defaults(manager: RunManager):
    """Create with no optional args should use defaults."""
    record = await manager.create("thread-1")
    assert record.metadata == {}
    assert record.kwargs == {}
    assert record.multitask_strategy == "reject"
    assert record.assistant_id is None


@pytest.mark.anyio
async def test_get_hydrates_store_only_record():
    """A fresh manager should restore historical runs from the persistent store."""
    store = MemoryRunStore()
    manager = RunManager(store=store)
    record = await manager.create_or_reject(
        "thread-1",
        "chat_lead_agent",
        metadata={"user_id": "user-1"},
        kwargs={"input": {"messages": []}},
    )

    restarted = RunManager(store=store)
    hydrated = await restarted.get(record.run_id, user_id="user-1")

    assert hydrated is not None
    assert hydrated.store_only is True
    assert hydrated.run_id == record.run_id
    assert hydrated.thread_id == "thread-1"
    assert hydrated.status == RunStatus.pending
    assert await restarted.get(record.run_id, user_id="other-user") is None


@pytest.mark.anyio
async def test_list_by_thread_merges_memory_and_store_records_newest_first(monkeypatch: pytest.MonkeyPatch):
    """Historical rows should appear beside live in-memory runs without duplicates."""
    store = MemoryRunStore()
    first_manager = RunManager(store=store)
    monkeypatch.setattr("deerflow.runtime.runs.manager._now_iso", lambda: "2026-01-01T00:00:00+00:00")
    historical = await first_manager.create_or_reject("thread-1", metadata={"user_id": "user-1"})

    second_manager = RunManager(store=store)
    monkeypatch.setattr("deerflow.runtime.runs.manager._now_iso", lambda: "2026-01-01T00:00:01+00:00")
    live = await second_manager.create_or_reject("thread-1", metadata={"user_id": "user-1"})

    runs = await second_manager.list_by_thread("thread-1", user_id="user-1")

    assert [run.run_id for run in runs] == [live.run_id, historical.run_id]
    assert runs[0].store_only is False
    assert runs[1].store_only is True


@pytest.mark.anyio
async def test_cancel_persists_interrupted_status_for_restarted_manager():
    """Interrupted status should survive a RunManager restart."""
    store = MemoryRunStore()
    manager = RunManager(store=store)
    record = await manager.create_or_reject("thread-1", metadata={"user_id": "user-1"})
    await manager.set_status(record.run_id, RunStatus.running)

    assert await manager.cancel(record.run_id) is True

    restarted = RunManager(store=store)
    hydrated = await restarted.get(record.run_id, user_id="user-1")
    assert hydrated is not None
    assert hydrated.status == RunStatus.interrupted
    assert hydrated.store_only is True


@pytest.mark.anyio
async def test_create_or_reject_rejects_only_same_thread_inflight():
    """Reject strategy should not scan or conflict with other thread activity."""
    manager = RunManager()
    other = await manager.create_or_reject("thread-2")

    created = await manager.create_or_reject("thread-1", multitask_strategy="reject")

    assert created.thread_id == "thread-1"
    assert other.status == RunStatus.pending


@pytest.mark.anyio
async def test_create_or_reject_interrupts_only_same_thread_inflight():
    """Interrupt/rollback strategies should cancel only target-thread inflight runs."""
    manager = RunManager()
    same_thread = await manager.create_or_reject("thread-1")
    other_thread = await manager.create_or_reject("thread-2")
    await manager.set_status(same_thread.run_id, RunStatus.running)
    await manager.set_status(other_thread.run_id, RunStatus.running)

    created = await manager.create_or_reject("thread-1", multitask_strategy="rollback")

    assert created.thread_id == "thread-1"
    assert same_thread.status == RunStatus.interrupted
    assert same_thread.abort_event.is_set()
    assert same_thread.abort_action == "rollback"
    assert other_thread.status == RunStatus.running
    assert not other_thread.abort_event.is_set()
    assert await manager.has_inflight("thread-1") is True
    assert await manager.has_inflight("thread-2") is True


@pytest.mark.anyio
async def test_model_name_create_or_reject_persists_to_store():
    """create_or_reject should persist the requested model_name."""
    store = MemoryRunStore()
    manager = RunManager(store=store)

    record = await manager.create_or_reject("thread-1", model_name=" deepseek-v3 ")

    assert record.model_name == " deepseek-v3 "
    stored = await store.get(record.run_id)
    assert stored is not None
    assert stored["model_name"] == "deepseek-v3"


@pytest.mark.anyio
async def test_update_model_name_normalizes_and_persists():
    """update_model_name should update memory and store consistently."""
    store = MemoryRunStore()
    manager = RunManager(store=store)
    record = await manager.create_or_reject("thread-1")
    long_model_name = " " + ("x" * 140) + " "

    await manager.update_model_name(record.run_id, long_model_name)

    assert record.model_name == long_model_name
    stored = await store.get(record.run_id)
    assert stored is not None
    assert stored["model_name"] == "x" * 128


@pytest.mark.anyio
async def test_update_run_completion_persists_token_totals_and_aggregates():
    """RunStore should expose thread-level token usage totals."""
    store = MemoryRunStore()
    manager = RunManager(store=store)
    record = await manager.create_or_reject("thread-1", model_name="model-a")
    await manager.set_status(record.run_id, RunStatus.running)

    await manager.update_run_completion(
        record.run_id,
        total_input_tokens=10,
        total_output_tokens=5,
        total_tokens=15,
        llm_call_count=1,
        lead_agent_tokens=9,
        subagent_tokens=6,
        middleware_tokens=0,
        message_count=3,
    )
    await manager.set_status(record.run_id, RunStatus.success)

    stored = await store.get(record.run_id)
    assert stored is not None
    assert stored["total_tokens"] == 15
    assert stored["subagent_tokens"] == 6

    aggregate = await manager.aggregate_tokens_by_thread("thread-1")
    assert aggregate["total_tokens"] == 15
    assert aggregate["total_input_tokens"] == 10
    assert aggregate["total_output_tokens"] == 5
    assert aggregate["total_runs"] == 1
    assert aggregate["by_model"] == {"model-a": {"tokens": 15, "runs": 1}}
    assert aggregate["by_caller"] == {"lead_agent": 9, "subagent": 6, "middleware": 0}


@pytest.mark.anyio
async def test_update_run_progress_is_only_included_when_requested():
    """Running snapshots should not affect default historical totals."""
    store = MemoryRunStore()
    manager = RunManager(store=store)
    record = await manager.create_or_reject("thread-1", model_name="model-a")
    await manager.set_status(record.run_id, RunStatus.running)

    await manager.update_run_progress(record.run_id, total_tokens=7, total_input_tokens=4, total_output_tokens=3)

    assert (await manager.aggregate_tokens_by_thread("thread-1"))["total_tokens"] == 0
    assert (await manager.aggregate_tokens_by_thread("thread-1", include_active=True))["total_tokens"] == 7
