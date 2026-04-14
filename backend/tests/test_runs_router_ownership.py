"""Tests for ownership enforcement on runs routes.

Covers:
- Unauthenticated access to thread-scoped runs returns 401
- Owner match allows access
- Owner mismatch returns 404
- Stateless /api/runs endpoints bind new threads to authenticated user
- Stateless /api/runs with caller-supplied thread_id owned by another user returns 404
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.gateway.routers import thread_runs, runs as runs_router

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

USER_A = "user-aaaa-1111"
USER_B = "user-bbbb-2222"
THREAD_1 = "thread-0001"
RUN_1 = "run-0001"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_store_item(user_id: str):
    item = MagicMock()
    item.value = {"user_id": user_id}
    return item


def _make_store(*, owner: str | None = None):
    store = MagicMock()

    async def _aget(ns, key):
        if "thread_owners" in str(ns):
            return _make_store_item(owner) if owner else None
        return None

    store.aget = AsyncMock(side_effect=_aget)
    store.aput = AsyncMock()
    store.adelete = AsyncMock()
    store.asearch = AsyncMock(return_value=[])
    return store


def _make_run_record(thread_id: str = THREAD_1, run_id: str = RUN_1):
    record = MagicMock()
    record.run_id = run_id
    record.thread_id = thread_id
    record.assistant_id = None
    record.status = MagicMock()
    record.status.value = "idle"
    record.metadata = {}
    record.kwargs = {}
    record.multitask_strategy = "reject"
    record.created_at = ""
    record.updated_at = ""
    record.task = None
    record.error = None
    record.on_disconnect = MagicMock()
    return record


def _make_run_manager(*, run_record=None):
    mgr = MagicMock()
    mgr.create_or_reject = AsyncMock(return_value=run_record or _make_run_record())
    mgr.list_by_thread = AsyncMock(return_value=[])
    mgr.get = MagicMock(return_value=run_record or _make_run_record())
    mgr.cancel = AsyncMock(return_value=True)
    return mgr


def _make_checkpointer():
    cp = MagicMock()
    cp.aget_tuple = AsyncMock(return_value=None)
    cp.aput = AsyncMock(return_value={"configurable": {"checkpoint_id": "ckpt-001"}})
    return cp


def _make_stream_bridge():
    bridge = MagicMock()

    async def _subscribe(*args, **kwargs):
        return
        yield  # make it an async generator

    bridge.subscribe = _subscribe
    return bridge


def _make_app_thread_runs(*, owner: str | None = None):
    app = FastAPI()
    app.include_router(thread_runs.router)
    app.state.store = _make_store(owner=owner)
    app.state.checkpointer = _make_checkpointer()
    app.state.run_manager = _make_run_manager()
    app.state.stream_bridge = _make_stream_bridge()
    return app


def _make_app_runs(*, owner: str | None = None):
    app = FastAPI()
    app.include_router(runs_router.router)
    app.state.store = _make_store(owner=owner)
    app.state.checkpointer = _make_checkpointer()
    app.state.run_manager = _make_run_manager()
    app.state.stream_bridge = _make_stream_bridge()
    return app


def _patch_auth(user_id: str | None):
    if user_id is None:
        return patch(
            "app.gateway.deps.get_current_user_id",
            new=AsyncMock(side_effect=HTTPException(status_code=401, detail="Authentication required")),
        )
    return patch(
        "app.gateway.deps.get_current_user_id",
        new=AsyncMock(return_value=user_id),
    )


def _patch_optional_auth(user_id: str | None):
    return patch(
        "app.gateway.deps.get_optional_user_id",
        return_value=user_id,
    )


def _patch_start_run(run_record=None):
    return patch(
        "app.gateway.routers.thread_runs.start_run",
        new=AsyncMock(return_value=run_record or _make_run_record()),
    )


def _patch_start_run_stateless(run_record=None):
    return patch(
        "app.gateway.routers.runs.start_run",
        new=AsyncMock(return_value=run_record or _make_run_record()),
    )


# ---------------------------------------------------------------------------
# POST /api/threads/{thread_id}/runs
# ---------------------------------------------------------------------------


class TestCreateRun:
    def test_unauthenticated_returns_401(self):
        app = _make_app_thread_runs(owner=USER_A)
        with _patch_auth(None):
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.post(f"/api/threads/{THREAD_1}/runs", json={})
        assert resp.status_code == 401

    def test_owner_match_returns_200(self):
        app = _make_app_thread_runs(owner=USER_A)
        with _patch_auth(USER_A), _patch_start_run():
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.post(f"/api/threads/{THREAD_1}/runs", json={})
        assert resp.status_code == 200

    def test_owner_mismatch_returns_404(self):
        app = _make_app_thread_runs(owner=USER_B)
        with _patch_auth(USER_A):
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.post(f"/api/threads/{THREAD_1}/runs", json={})
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/threads/{thread_id}/runs
# ---------------------------------------------------------------------------


class TestListRuns:
    def test_unauthenticated_returns_401(self):
        app = _make_app_thread_runs(owner=USER_A)
        with _patch_auth(None):
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.get(f"/api/threads/{THREAD_1}/runs")
        assert resp.status_code == 401

    def test_owner_match_returns_200(self):
        app = _make_app_thread_runs(owner=USER_A)
        with _patch_auth(USER_A):
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.get(f"/api/threads/{THREAD_1}/runs")
        assert resp.status_code == 200

    def test_owner_mismatch_returns_404(self):
        app = _make_app_thread_runs(owner=USER_B)
        with _patch_auth(USER_A):
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.get(f"/api/threads/{THREAD_1}/runs")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/threads/{thread_id}/runs/{run_id}
# ---------------------------------------------------------------------------


class TestGetRun:
    def test_unauthenticated_returns_401(self):
        app = _make_app_thread_runs(owner=USER_A)
        with _patch_auth(None):
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.get(f"/api/threads/{THREAD_1}/runs/{RUN_1}")
        assert resp.status_code == 401

    def test_owner_match_returns_200(self):
        app = _make_app_thread_runs(owner=USER_A)
        with _patch_auth(USER_A):
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.get(f"/api/threads/{THREAD_1}/runs/{RUN_1}")
        assert resp.status_code == 200

    def test_owner_mismatch_returns_404(self):
        app = _make_app_thread_runs(owner=USER_B)
        with _patch_auth(USER_A):
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.get(f"/api/threads/{THREAD_1}/runs/{RUN_1}")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/threads/{thread_id}/runs/{run_id}/cancel
# ---------------------------------------------------------------------------


class TestCancelRun:
    def test_unauthenticated_returns_401(self):
        app = _make_app_thread_runs(owner=USER_A)
        with _patch_auth(None):
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.post(f"/api/threads/{THREAD_1}/runs/{RUN_1}/cancel")
        assert resp.status_code == 401

    def test_owner_match_returns_202(self):
        app = _make_app_thread_runs(owner=USER_A)
        with _patch_auth(USER_A):
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.post(f"/api/threads/{THREAD_1}/runs/{RUN_1}/cancel")
        assert resp.status_code == 202

    def test_owner_mismatch_returns_404(self):
        app = _make_app_thread_runs(owner=USER_B)
        with _patch_auth(USER_A):
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.post(f"/api/threads/{THREAD_1}/runs/{RUN_1}/cancel")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/threads/{thread_id}/runs/wait
# ---------------------------------------------------------------------------


class TestWaitRun:
    def test_unauthenticated_returns_401(self):
        app = _make_app_thread_runs(owner=USER_A)
        with _patch_auth(None):
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.post(f"/api/threads/{THREAD_1}/runs/wait", json={})
        assert resp.status_code == 401

    def test_owner_match_returns_200(self):
        app = _make_app_thread_runs(owner=USER_A)
        with _patch_auth(USER_A), _patch_start_run():
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.post(f"/api/threads/{THREAD_1}/runs/wait", json={})
        assert resp.status_code == 200

    def test_owner_mismatch_returns_404(self):
        app = _make_app_thread_runs(owner=USER_B)
        with _patch_auth(USER_A):
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.post(f"/api/threads/{THREAD_1}/runs/wait", json={})
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Stateless /api/runs/wait — caller-supplied thread_id ownership check
# ---------------------------------------------------------------------------


class TestStatelessWait:
    def test_caller_supplied_thread_id_owned_by_other_user_returns_404(self):
        """Caller provides a thread_id owned by USER_B; USER_A gets 404."""
        app = _make_app_runs(owner=USER_B)
        body = {"config": {"configurable": {"thread_id": THREAD_1}}}
        with _patch_auth(USER_A), _patch_optional_auth(USER_A):
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.post("/api/runs/wait", json=body)
        assert resp.status_code == 404

    def test_caller_supplied_thread_id_owned_by_same_user_returns_200(self):
        """Caller provides a thread_id they own; run proceeds."""
        app = _make_app_runs(owner=USER_A)
        body = {"config": {"configurable": {"thread_id": THREAD_1}}}
        with _patch_auth(USER_A), _patch_optional_auth(USER_A), _patch_start_run_stateless():
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.post("/api/runs/wait", json=body)
        assert resp.status_code == 200

    def test_no_thread_id_auto_generates_and_binds(self):
        """No thread_id in body — auto-generates and binds to authenticated user."""
        app = _make_app_runs()
        with _patch_optional_auth(USER_A), _patch_start_run_stateless():
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.post("/api/runs/wait", json={})
        assert resp.status_code == 200
