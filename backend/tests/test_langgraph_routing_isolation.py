"""Regression tests for US-006: LangGraph traffic routed through authenticated Gateway.

These tests assert that the Gateway's thread/run/state/history endpoints enforce
owner checks — i.e. the default /api/langgraph/* route (which rewrites to /api/*)
does NOT bypass Gateway owner-check middleware.

The nginx rewrite is a config-level concern; here we verify the Gateway API layer
itself enforces ownership so that no nginx misconfiguration can silently bypass it.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.gateway.routers import thread_runs, threads

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

USER_A = "user-aaaa-1111"
USER_B = "user-bbbb-2222"
THREAD_1 = "thread-route-001"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_store(*, owner: str | None = None):
    store = MagicMock()

    async def _aget(ns, key):
        if "thread_owners" in str(ns):
            if owner:
                item = MagicMock()
                item.value = {"user_id": owner}
                return item
        return None

    store.aget = AsyncMock(side_effect=_aget)
    store.aput = AsyncMock()
    store.adelete = AsyncMock()
    store.asearch = AsyncMock(return_value=[])
    return store


def _make_checkpointer():
    cp = MagicMock()
    cp.aget_tuple = AsyncMock(return_value=None)
    cp.aput = AsyncMock(return_value={"configurable": {"checkpoint_id": "ckpt-001"}})

    async def _alist(*args, **kwargs):
        return
        yield

    cp.alist = _alist
    return cp


def _make_run_manager():
    mgr = MagicMock()
    mgr.list_by_thread = AsyncMock(return_value=[])
    mgr.get = MagicMock(return_value=None)
    mgr.cancel = AsyncMock(return_value=False)
    return mgr


def _make_stream_bridge():
    bridge = MagicMock()
    return bridge


def _make_app(*, owner: str | None = None):
    app = FastAPI()
    app.include_router(threads.router)
    app.include_router(thread_runs.router)
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


# ---------------------------------------------------------------------------
# Assertion: Gateway thread routes enforce ownership
# (These are the routes that /api/langgraph/* rewrites to via nginx)
# ---------------------------------------------------------------------------


class TestDefaultRouteEnforcesOwnership:
    """Assert that the Gateway endpoints reachable via /api/langgraph/* rewrite
    enforce owner checks — so the default nginx route cannot bypass isolation."""

    def test_get_thread_state_unauthenticated_returns_401(self):
        """GET /api/threads/{id}/state requires authentication."""
        app = _make_app(owner=USER_A)
        with _patch_auth(None):
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.get(f"/api/threads/{THREAD_1}/state")
        assert resp.status_code == 401

    def test_get_thread_state_wrong_owner_returns_404(self):
        """GET /api/threads/{id}/state denies cross-user access."""
        app = _make_app(owner=USER_B)
        with _patch_auth(USER_A):
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.get(f"/api/threads/{THREAD_1}/state")
        assert resp.status_code == 404

    def test_post_thread_history_unauthenticated_returns_401(self):
        """POST /api/threads/{id}/history requires authentication."""
        app = _make_app(owner=USER_A)
        with _patch_auth(None):
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.post(f"/api/threads/{THREAD_1}/history", json={})
        assert resp.status_code == 401

    def test_post_thread_history_wrong_owner_returns_404(self):
        """POST /api/threads/{id}/history denies cross-user access."""
        app = _make_app(owner=USER_B)
        with _patch_auth(USER_A):
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.post(f"/api/threads/{THREAD_1}/history", json={})
        assert resp.status_code == 404

    def test_list_runs_unauthenticated_returns_401(self):
        """GET /api/threads/{id}/runs requires authentication."""
        app = _make_app(owner=USER_A)
        with _patch_auth(None):
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.get(f"/api/threads/{THREAD_1}/runs")
        assert resp.status_code == 401

    def test_list_runs_wrong_owner_returns_404(self):
        """GET /api/threads/{id}/runs denies cross-user access."""
        app = _make_app(owner=USER_B)
        with _patch_auth(USER_A):
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.get(f"/api/threads/{THREAD_1}/runs")
        assert resp.status_code == 404

    def test_create_run_unauthenticated_returns_401(self):
        """POST /api/threads/{id}/runs requires authentication."""
        app = _make_app(owner=USER_A)
        with _patch_auth(None):
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.post(f"/api/threads/{THREAD_1}/runs", json={})
        assert resp.status_code == 401

    def test_create_run_wrong_owner_returns_404(self):
        """POST /api/threads/{id}/runs denies cross-user access."""
        app = _make_app(owner=USER_B)
        with _patch_auth(USER_A):
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.post(f"/api/threads/{THREAD_1}/runs", json={})
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Assertion: nginx config default routes through Gateway (config assertion)
# ---------------------------------------------------------------------------


def test_nginx_local_conf_default_routes_to_gateway():
    """Assert nginx.local.conf routes /api/langgraph/ to gateway by default.

    Reads the nginx config file and verifies:
    - The /api/langgraph/ location rewrites to /api/ (Gateway path)
    - It proxies to http://gateway (not http://langgraph)
    """
    import re
    from pathlib import Path

    conf_path = Path(__file__).parent.parent.parent / "docker" / "nginx" / "nginx.local.conf"
    assert conf_path.exists(), f"nginx.local.conf not found at {conf_path}"

    content = conf_path.read_text()

    # Find the /api/langgraph/ location block
    # Match from "location /api/langgraph/" to the closing "}"
    block_match = re.search(
        r"location\s+/api/langgraph/\s*\{([^}]+)\}",
        content,
        re.DOTALL,
    )
    assert block_match, "Could not find /api/langgraph/ location block in nginx.local.conf"
    block = block_match.group(1)

    # The rewrite must target /api/ (Gateway path), not / (LangGraph direct)
    assert "rewrite" in block, "No rewrite directive in /api/langgraph/ block"
    rewrite_match = re.search(r"rewrite\s+\S+\s+(\S+)\s+break", block)
    assert rewrite_match, "Could not parse rewrite target"
    rewrite_target = rewrite_match.group(1)
    assert rewrite_target.startswith("/api/"), (
        f"Default /api/langgraph/ rewrite target should start with /api/ (Gateway), "
        f"got: {rewrite_target!r}"
    )

    # The proxy_pass must point to gateway, not langgraph
    assert "proxy_pass http://gateway" in block, (
        "Default /api/langgraph/ location must proxy to http://gateway "
        "(not http://langgraph) to enforce owner checks"
    )


def test_docker_compose_dev_default_routes_to_gateway():
    """Assert docker-compose-dev.yaml defaults LANGGRAPH_UPSTREAM to gateway:8001."""
    from pathlib import Path

    compose_path = Path(__file__).parent.parent.parent / "docker" / "docker-compose-dev.yaml"
    assert compose_path.exists(), f"docker-compose-dev.yaml not found at {compose_path}"

    content = compose_path.read_text()

    # The default LANGGRAPH_UPSTREAM must be gateway:8001
    assert "LANGGRAPH_UPSTREAM:-gateway:8001" in content, (
        "docker-compose-dev.yaml LANGGRAPH_UPSTREAM default must be gateway:8001 "
        "to route /api/langgraph/* through authenticated Gateway"
    )
    # The default LANGGRAPH_REWRITE must be /api/
    assert "LANGGRAPH_REWRITE:-/api/" in content, (
        "docker-compose-dev.yaml LANGGRAPH_REWRITE default must be /api/ "
        "so rewrites target Gateway API paths"
    )
