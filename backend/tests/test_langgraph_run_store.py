from types import SimpleNamespace

import pytest

from deerflow.runtime.runs.store.langgraph import LangGraphRunStore


class RecordingStore:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows
        self.asearch_calls: list[dict] = []

    async def asearch(self, namespace_prefix, /, **kwargs):
        self.asearch_calls.append({"namespace": namespace_prefix, **kwargs})
        return [SimpleNamespace(value=row) for row in self.rows]


@pytest.mark.anyio
async def test_langgraph_run_store_list_by_thread_pushes_thread_and_user_filter():
    store = RecordingStore(
        [
            {
                "run_id": "old",
                "thread_id": "thread-1",
                "user_id": "user-1",
                "created_at": "2026-01-01T00:00:00+00:00",
            },
            {
                "run_id": "new",
                "thread_id": "thread-1",
                "user_id": "user-1",
                "created_at": "2026-01-01T00:00:01+00:00",
            },
            {
                "run_id": "other-thread",
                "thread_id": "thread-2",
                "user_id": "user-1",
                "created_at": "2026-01-01T00:00:02+00:00",
            },
            {
                "run_id": "other-user",
                "thread_id": "thread-1",
                "user_id": "user-2",
                "created_at": "2026-01-01T00:00:03+00:00",
            },
        ]
    )
    run_store = LangGraphRunStore(store)

    rows = await run_store.list_by_thread("thread-1", user_id="user-1", limit=2)

    assert store.asearch_calls == [
        {
            "namespace": ("runs",),
            "filter": {"thread_id": "thread-1", "user_id": "user-1"},
            "limit": 10_000,
        }
    ]
    assert [row["run_id"] for row in rows] == ["new", "old"]


@pytest.mark.anyio
async def test_langgraph_run_store_aggregate_pushes_thread_filter_and_excludes_active():
    store = RecordingStore(
        [
            {
                "run_id": "success",
                "thread_id": "thread-1",
                "status": "success",
                "model_name": "model-a",
                "total_input_tokens": 2,
                "total_output_tokens": 3,
                "total_tokens": 5,
                "lead_agent_tokens": 5,
            },
            {
                "run_id": "running",
                "thread_id": "thread-1",
                "status": "running",
                "model_name": "model-a",
                "total_tokens": 7,
            },
            {
                "run_id": "other-thread",
                "thread_id": "thread-2",
                "status": "success",
                "model_name": "model-b",
                "total_tokens": 11,
            },
        ]
    )
    run_store = LangGraphRunStore(store)

    aggregate = await run_store.aggregate_tokens_by_thread("thread-1")

    assert store.asearch_calls == [
        {
            "namespace": ("runs",),
            "filter": {"thread_id": "thread-1"},
            "limit": 10_000,
        }
    ]
    assert aggregate["total_tokens"] == 5
    assert aggregate["total_input_tokens"] == 2
    assert aggregate["total_output_tokens"] == 3
    assert aggregate["total_runs"] == 1
    assert aggregate["by_model"] == {"model-a": {"tokens": 5, "runs": 1}}
