import re
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI, HTTPException
import asyncio

from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore

from app.gateway.routers import threads
from app.gateway.user_prefix import user_threads_namespace
from deerflow.config.paths import Paths

_ISO_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
_TEST_USER_ID = "user-test"


def _build_thread_app() -> tuple[FastAPI, InMemoryStore, InMemorySaver]:
    """Build a FastAPI app with the fork's user-scoped Store/checkpointer."""
    app = FastAPI()
    store = InMemoryStore()
    checkpointer = InMemorySaver()
    app.state.store = store
    app.state.checkpointer = checkpointer
    app.include_router(threads.router)
    return app, store, checkpointer


def test_delete_thread_data_removes_thread_directory(tmp_path):
    paths = Paths(tmp_path)
    thread_dir = paths.thread_dir("thread-cleanup")
    workspace = paths.sandbox_work_dir("thread-cleanup")
    uploads = paths.sandbox_uploads_dir("thread-cleanup")
    outputs = paths.sandbox_outputs_dir("thread-cleanup")

    for directory in [workspace, uploads, outputs]:
        directory.mkdir(parents=True, exist_ok=True)
    (workspace / "notes.txt").write_text("hello", encoding="utf-8")
    (uploads / "report.pdf").write_bytes(b"pdf")
    (outputs / "result.json").write_text("{}", encoding="utf-8")

    assert thread_dir.exists()

    response = threads._delete_thread_data("thread-cleanup", paths=paths)

    assert response.success is True
    assert not thread_dir.exists()


def test_delete_thread_data_is_idempotent_for_missing_directory(tmp_path):
    paths = Paths(tmp_path)

    response = threads._delete_thread_data("missing-thread", paths=paths)

    assert response.success is True
    assert not paths.thread_dir("missing-thread").exists()


def test_delete_thread_data_rejects_invalid_thread_id(tmp_path):
    paths = Paths(tmp_path)

    with pytest.raises(HTTPException) as exc_info:
        threads._delete_thread_data("../escape", paths=paths)

    assert exc_info.value.status_code == 422
    assert "Invalid thread_id" in exc_info.value.detail


def test_delete_thread_route_cleans_thread_directory(tmp_path):
    from unittest.mock import AsyncMock

    paths = Paths(tmp_path)
    thread_dir = paths.thread_dir("thread-route")
    paths.sandbox_work_dir("thread-route").mkdir(parents=True, exist_ok=True)
    (paths.sandbox_work_dir("thread-route") / "notes.txt").write_text("hello", encoding="utf-8")

    app = FastAPI()
    app.include_router(threads.router)

    with (
        patch("app.gateway.routers.threads.get_paths", return_value=paths),
        patch("app.gateway.deps.get_current_user_id", new=AsyncMock(return_value="user-test")),
        patch("app.gateway.routers.threads.require_thread_owner", new=AsyncMock(return_value="user-test")),
    ):
        with TestClient(app) as client:
            response = client.delete("/api/threads/thread-route")

    assert response.status_code == 200
    assert response.json() == {"success": True, "message": "Deleted local thread data for thread-route"}
    assert not thread_dir.exists()


def test_delete_thread_route_rejects_invalid_thread_id(tmp_path):
    paths = Paths(tmp_path)

    app = FastAPI()
    app.include_router(threads.router)

    with patch("app.gateway.routers.threads.get_paths", return_value=paths):
        with TestClient(app) as client:
            response = client.delete("/api/threads/../escape")

    assert response.status_code == 404


def test_delete_thread_route_returns_422_for_route_safe_invalid_id(tmp_path):
    from unittest.mock import AsyncMock

    paths = Paths(tmp_path)

    app = FastAPI()
    app.include_router(threads.router)

    with (
        patch("app.gateway.routers.threads.get_paths", return_value=paths),
        patch("app.gateway.deps.get_current_user_id", new=AsyncMock(return_value="user-test")),
        patch("app.gateway.routers.threads.require_thread_owner", new=AsyncMock(return_value="user-test")),
    ):
        with TestClient(app) as client:
            response = client.delete("/api/threads/thread.with.dot")

    assert response.status_code == 422
    assert "Invalid thread_id" in response.json()["detail"]


def test_delete_thread_data_returns_generic_500_error(tmp_path):
    paths = Paths(tmp_path)

    with (
        patch.object(paths, "delete_thread_dir", side_effect=OSError("/secret/path")),
        patch.object(threads.logger, "exception") as log_exception,
    ):
        with pytest.raises(HTTPException) as exc_info:
            threads._delete_thread_data("thread-cleanup", paths=paths)

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Failed to delete local thread data."
    assert "/secret/path" not in exc_info.value.detail
    log_exception.assert_called_once_with("Failed to delete thread data for %s", "thread-cleanup")


# ── Server-reserved metadata key stripping ──────────────────────────────────


def test_strip_reserved_metadata_removes_user_id():
    """Client-supplied user_id is dropped to prevent reflection attacks."""
    out = threads._strip_reserved_metadata({"user_id": "victim-id", "title": "ok"})
    assert out == {"title": "ok"}


def test_strip_reserved_metadata_passes_through_safe_keys():
    """Non-reserved keys are preserved verbatim."""
    md = {"title": "ok", "tags": ["a", "b"], "custom": {"x": 1}}
    assert threads._strip_reserved_metadata(md) == md


def test_strip_reserved_metadata_empty_input():
    """Empty / None metadata returns same object — no crash."""
    assert threads._strip_reserved_metadata({}) == {}


def test_strip_reserved_metadata_strips_all_reserved_keys():
    out = threads._strip_reserved_metadata({"user_id": "x", "keep": "me"})
    assert out == {"keep": "me"}


# ---------------------------------------------------------------------------
# ISO 8601 timestamp contract (issue #2594)
# ---------------------------------------------------------------------------
#
# Threads endpoints document ``created_at`` / ``updated_at`` as ISO
# timestamps and that is the format LangGraph Platform uses
# (``langgraph_sdk.schema.Thread.created_at: datetime`` JSON-encodes to
# ISO 8601). The tests below pin that contract end-to-end and also
# exercise the ``coerce_iso`` healing path for legacy unix-timestamp
# records written by older Gateway versions.


def test_create_thread_returns_iso_timestamps() -> None:
    app, _store, _checkpointer = _build_thread_app()

    with patch(
        "app.gateway.routers.threads.get_optional_user_from_request",
        new=AsyncMock(return_value=SimpleNamespace(id=_TEST_USER_ID)),
    ):
        with TestClient(app) as client:
            response = client.post("/api/threads", json={"metadata": {}})

    assert response.status_code == 200, response.text
    body = response.json()
    assert _ISO_TIMESTAMP_RE.match(body["created_at"]), body["created_at"]
    assert _ISO_TIMESTAMP_RE.match(body["updated_at"]), body["updated_at"]
    assert body["created_at"] == body["updated_at"]


def test_get_thread_returns_iso_for_legacy_unix_record() -> None:
    app, store, checkpointer = _build_thread_app()
    legacy_thread_id = "legacy-thread"
    legacy_ts = "1777252410.411327"

    async def _seed() -> None:
        from langgraph.checkpoint.base import empty_checkpoint

        await store.aput(
            user_threads_namespace(_TEST_USER_ID),
            legacy_thread_id,
            {
                "thread_id": legacy_thread_id,
                "status": "idle",
                "created_at": legacy_ts,
                "updated_at": legacy_ts,
                "metadata": {},
            },
        )
        await checkpointer.aput(
            {"configurable": {"thread_id": legacy_thread_id, "checkpoint_ns": ""}},
            empty_checkpoint(),
            {"step": -1, "source": "input", "writes": None, "parents": {}},
            {},
        )

    asyncio.run(_seed())

    with patch("app.gateway.routers.threads.require_thread_owner", new=AsyncMock(return_value=_TEST_USER_ID)):
        with TestClient(app) as client:
            response = client.get(f"/api/threads/{legacy_thread_id}")

    assert response.status_code == 200, response.text
    body = response.json()
    assert _ISO_TIMESTAMP_RE.match(body["created_at"]), body["created_at"]
    assert _ISO_TIMESTAMP_RE.match(body["updated_at"]), body["updated_at"]


def test_patch_thread_returns_iso_and_advances_updated_at() -> None:
    app, store, _checkpointer = _build_thread_app()
    thread_id = "patch-target"

    async def _seed() -> None:
        await store.aput(
            user_threads_namespace(_TEST_USER_ID),
            thread_id,
            {
                "thread_id": thread_id,
                "status": "idle",
                "created_at": "1777000000.000000",
                "updated_at": "1777000000.000000",
                "metadata": {"k": "v0"},
            },
        )

    asyncio.run(_seed())

    with patch("app.gateway.routers.threads.require_thread_owner", new=AsyncMock(return_value=_TEST_USER_ID)):
        with TestClient(app) as client:
            response = client.patch(f"/api/threads/{thread_id}", json={"metadata": {"k": "v1", "user_id": "spoof"}})

    assert response.status_code == 200, response.text
    body = response.json()
    assert _ISO_TIMESTAMP_RE.match(body["created_at"]), body["created_at"]
    assert _ISO_TIMESTAMP_RE.match(body["updated_at"]), body["updated_at"]
    assert body["updated_at"] > body["created_at"]
    assert body["metadata"] == {"k": "v1"}


def test_search_threads_normalizes_legacy_unix_seconds_to_iso() -> None:
    app, store, _checkpointer = _build_thread_app()

    async def _seed() -> None:
        ns = user_threads_namespace(_TEST_USER_ID)
        await store.aput(
            ns,
            "legacy",
            {
                "thread_id": "legacy",
                "status": "idle",
                "created_at": 1777000000.0,
                "updated_at": 1777000000.0,
                "metadata": {},
            },
        )
        await store.aput(
            ns,
            "modern",
            {
                "thread_id": "modern",
                "status": "idle",
                "created_at": "2026-04-27T00:00:00+00:00",
                "updated_at": "2026-04-27T00:00:00+00:00",
                "metadata": {},
            },
        )

    asyncio.run(_seed())

    with patch("app.gateway.routers.threads.get_optional_user_id", return_value=_TEST_USER_ID):
        with TestClient(app) as client:
            response = client.post("/api/threads/search", json={"limit": 10})

    assert response.status_code == 200, response.text
    items = response.json()
    assert {item["thread_id"] for item in items} == {"legacy", "modern"}
    for item in items:
        assert _ISO_TIMESTAMP_RE.match(item["created_at"]), item
        assert _ISO_TIMESTAMP_RE.match(item["updated_at"]), item


def test_get_thread_state_returns_iso_for_legacy_checkpoint_metadata() -> None:
    app, _store, checkpointer = _build_thread_app()
    thread_id = "legacy-state"

    async def _seed() -> None:
        from langgraph.checkpoint.base import empty_checkpoint

        await checkpointer.aput(
            {"configurable": {"thread_id": thread_id, "checkpoint_ns": ""}},
            empty_checkpoint(),
            {"step": -1, "source": "input", "writes": None, "parents": {}, "created_at": 1777252410.411327},
            {},
        )

    asyncio.run(_seed())

    with patch("app.gateway.routers.threads.require_thread_owner", new=AsyncMock(return_value=_TEST_USER_ID)):
        with TestClient(app) as client:
            response = client.get(f"/api/threads/{thread_id}/state")

    assert response.status_code == 200, response.text
    body = response.json()
    assert _ISO_TIMESTAMP_RE.match(body["created_at"]), body["created_at"]
    assert _ISO_TIMESTAMP_RE.match(body["checkpoint"]["ts"]), body["checkpoint"]


def test_get_thread_history_returns_iso_for_legacy_checkpoint_metadata() -> None:
    app, _store, checkpointer = _build_thread_app()
    thread_id = "legacy-history"

    async def _seed() -> None:
        from langgraph.checkpoint.base import empty_checkpoint

        await checkpointer.aput(
            {"configurable": {"thread_id": thread_id, "checkpoint_ns": ""}},
            empty_checkpoint(),
            {"step": -1, "source": "input", "writes": None, "parents": {}, "created_at": 1777252410.411327},
            {},
        )

    asyncio.run(_seed())

    with patch("app.gateway.routers.threads.require_thread_owner", new=AsyncMock(return_value=_TEST_USER_ID)):
        with TestClient(app) as client:
            response = client.post(f"/api/threads/{thread_id}/history", json={"limit": 10})

    assert response.status_code == 200, response.text
    entries = response.json()
    assert entries, "expected at least one history entry"
    for entry in entries:
        assert _ISO_TIMESTAMP_RE.match(entry["created_at"]), entry
