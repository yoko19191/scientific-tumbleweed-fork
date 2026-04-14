"""Tests for ownership enforcement on thread CRUD and state routes.

Covers:
- Unauthenticated access returns 401
- Owner match allows access
- Owner mismatch returns 404
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.gateway.routers import threads

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

USER_A = "user-aaaa-1111"
USER_B = "user-bbbb-2222"
THREAD_1 = "thread-0001"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_store_item(user_id: str):
    item = MagicMock()
    item.value = {"user_id": user_id}
    return item


def _make_store(*, owner: str | None = None, thread_record: dict | None = None):
    """Return a mock Store."""
    store = MagicMock()

    async def _aget(ns, key):
        # Ownership namespace lookup
        if "thread_owners" in str(ns):
            return _make_store_item(owner) if owner else None
        # Thread record lookup
        if thread_record is not None:
            item = MagicMock()
            item.value = thread_record
            return item
        return None

    store.aget = AsyncMock(side_effect=_aget)
    store.aput = AsyncMock()
    store.adelete = AsyncMock()
    store.asearch = AsyncMock(return_value=[])
    return store


def _make_checkpointer(*, checkpoint_tuple=None):
    cp = MagicMock()
    cp.aget_tuple = AsyncMock(return_value=checkpoint_tuple)
    cp.aput = AsyncMock(return_value={"configurable": {"checkpoint_id": "ckpt-001"}})

    async def _alist(*args, **kwargs):
        return
        yield  # make it an async generator

    cp.alist = _alist
    return cp


def _make_app(*, owner: str | None = None, thread_record: dict | None = None, checkpoint_tuple=None):
    """Build a minimal FastAPI app with mocked state."""
    app = FastAPI()
    app.include_router(threads.router)
    app.state.store = _make_store(owner=owner, thread_record=thread_record)
    app.state.checkpointer = _make_checkpointer(checkpoint_tuple=checkpoint_tuple)
    return app


def _patch_auth(user_id: str | None):
    """Context manager that patches get_current_user_id."""
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
    """Context manager that patches get_optional_user_id."""
    return patch(
        "app.gateway.routers.threads.get_optional_user_id",
        return_value=user_id,
    )


# ---------------------------------------------------------------------------
# GET /api/threads/{thread_id}
# ---------------------------------------------------------------------------


class TestGetThread:
    def test_unauthenticated_returns_401(self):
        app = _make_app(owner=USER_A)
        with _patch_auth(None):
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.get(f"/api/threads/{THREAD_1}")
        assert resp.status_code == 401

    def test_owner_match_returns_200(self):
        import time

        record = {"thread_id": THREAD_1, "status": "idle", "created_at": time.time(), "updated_at": time.time(), "metadata": {}}
        app = _make_app(owner=USER_A, thread_record=record)
        with _patch_auth(USER_A):
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.get(f"/api/threads/{THREAD_1}")
        assert resp.status_code == 200

    def test_owner_mismatch_returns_404(self):
        app = _make_app(owner=USER_B)
        with _patch_auth(USER_A):
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.get(f"/api/threads/{THREAD_1}")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /api/threads/{thread_id}
# ---------------------------------------------------------------------------


class TestPatchThread:
    def test_unauthenticated_returns_401(self):
        app = _make_app(owner=USER_A)
        with _patch_auth(None):
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.patch(f"/api/threads/{THREAD_1}", json={"metadata": {}})
        assert resp.status_code == 401

    def test_owner_match_returns_200(self):
        import time

        record = {"thread_id": THREAD_1, "status": "idle", "created_at": time.time(), "updated_at": time.time(), "metadata": {}}
        app = _make_app(owner=USER_A, thread_record=record)
        with _patch_auth(USER_A):
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.patch(f"/api/threads/{THREAD_1}", json={"metadata": {"key": "val"}})
        assert resp.status_code == 200

    def test_owner_mismatch_returns_404(self):
        app = _make_app(owner=USER_B)
        with _patch_auth(USER_A):
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.patch(f"/api/threads/{THREAD_1}", json={"metadata": {}})
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/threads/{thread_id}
# ---------------------------------------------------------------------------


class TestDeleteThread:
    def test_unauthenticated_returns_401(self):
        app = _make_app(owner=USER_A)
        with _patch_auth(None):
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.delete(f"/api/threads/{THREAD_1}")
        assert resp.status_code == 401

    def test_owner_match_returns_200(self):
        app = _make_app(owner=USER_A)
        with _patch_auth(USER_A):
            with patch("app.gateway.routers.threads._delete_thread_data", return_value=threads.ThreadDeleteResponse(success=True, message="ok")):
                with TestClient(app, raise_server_exceptions=False) as client:
                    resp = client.delete(f"/api/threads/{THREAD_1}")
        assert resp.status_code == 200

    def test_owner_mismatch_returns_404(self):
        app = _make_app(owner=USER_B)
        with _patch_auth(USER_A):
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.delete(f"/api/threads/{THREAD_1}")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/threads/{thread_id}/state
# ---------------------------------------------------------------------------


class TestGetThreadState:
    def test_unauthenticated_returns_401(self):
        app = _make_app(owner=USER_A)
        with _patch_auth(None):
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.get(f"/api/threads/{THREAD_1}/state")
        assert resp.status_code == 401

    def test_owner_match_returns_200(self):
        ckpt = MagicMock()
        ckpt.checkpoint = {"channel_values": {}}
        ckpt.metadata = {}
        ckpt.config = {"configurable": {"checkpoint_id": "ckpt-001"}}
        ckpt.parent_config = None
        ckpt.tasks = []
        app = _make_app(owner=USER_A, checkpoint_tuple=ckpt)
        with _patch_auth(USER_A):
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.get(f"/api/threads/{THREAD_1}/state")
        assert resp.status_code == 200

    def test_owner_mismatch_returns_404(self):
        app = _make_app(owner=USER_B)
        with _patch_auth(USER_A):
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.get(f"/api/threads/{THREAD_1}/state")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/threads/{thread_id}/state
# ---------------------------------------------------------------------------


class TestUpdateThreadState:
    def test_unauthenticated_returns_401(self):
        app = _make_app(owner=USER_A)
        with _patch_auth(None):
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.post(f"/api/threads/{THREAD_1}/state", json={"values": {}})
        assert resp.status_code == 401

    def test_owner_match_returns_200(self):
        ckpt = MagicMock()
        ckpt.checkpoint = {"channel_values": {}}
        ckpt.metadata = {}
        ckpt.config = {"configurable": {"checkpoint_id": "ckpt-001"}}
        ckpt.parent_config = None
        ckpt.tasks = []
        app = _make_app(owner=USER_A, checkpoint_tuple=ckpt)
        with _patch_auth(USER_A):
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.post(f"/api/threads/{THREAD_1}/state", json={"values": {"key": "val"}})
        assert resp.status_code == 200

    def test_owner_mismatch_returns_404(self):
        app = _make_app(owner=USER_B)
        with _patch_auth(USER_A):
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.post(f"/api/threads/{THREAD_1}/state", json={"values": {}})
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/threads/{thread_id}/history
# ---------------------------------------------------------------------------


class TestGetThreadHistory:
    def test_unauthenticated_returns_401(self):
        app = _make_app(owner=USER_A)
        with _patch_auth(None):
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.post(f"/api/threads/{THREAD_1}/history", json={})
        assert resp.status_code == 401

    def test_owner_match_returns_200(self):
        app = _make_app(owner=USER_A)
        with _patch_auth(USER_A):
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.post(f"/api/threads/{THREAD_1}/history", json={})
        assert resp.status_code == 200

    def test_owner_mismatch_returns_404(self):
        app = _make_app(owner=USER_B)
        with _patch_auth(USER_A):
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.post(f"/api/threads/{THREAD_1}/history", json={})
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/threads/search
# ---------------------------------------------------------------------------


class TestSearchThreads:
    def test_unauthenticated_returns_empty_list(self):
        """Unauthenticated callers get an empty list (not 401)."""
        app = _make_app()
        with _patch_optional_auth(None):
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.post("/api/threads/search", json={})
        assert resp.status_code == 200
        assert resp.json() == []

    def test_authenticated_returns_user_threads(self):
        """Authenticated user gets threads from their scoped namespace."""
        app = _make_app(owner=USER_A)
        with _patch_optional_auth(USER_A):
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.post("/api/threads/search", json={})
        assert resp.status_code == 200
        # Store returns empty list by default — just verify no error
        assert isinstance(resp.json(), list)


# ---------------------------------------------------------------------------
# GET /api/threads/listByUser
# ---------------------------------------------------------------------------


class TestListByUser:
    def test_unauthenticated_returns_401(self):
        app = _make_app()
        with _patch_auth(None):
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.get("/api/threads/listByUser")
        assert resp.status_code == 401

    def test_authenticated_returns_list(self):
        app = _make_app(owner=USER_A)
        with _patch_auth(USER_A):
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.get("/api/threads/listByUser")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ---------------------------------------------------------------------------
# POST /api/threads/bindUser
# ---------------------------------------------------------------------------


class TestBindUser:
    def test_unauthenticated_returns_401(self):
        app = _make_app()
        with _patch_auth(None):
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.post("/api/threads/bindUser", json={"thread_id": THREAD_1})
        assert resp.status_code == 401

    def test_authenticated_binds_thread(self):
        app = _make_app()
        with _patch_auth(USER_A):
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.post("/api/threads/bindUser", json={"thread_id": THREAD_1})
        assert resp.status_code == 200
        assert resp.json() == {"success": True}
