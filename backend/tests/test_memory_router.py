"""Tests for the memory API router.

All endpoints now require authentication (get_current_user_id).
Tests use app.dependency_overrides to simulate authenticated requests.
"""

from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.gateway.deps import get_current_user_id
from app.gateway.routers import memory

USER_A = "user-aaaa-1111"
USER_B = "user-bbbb-2222"


def _sample_memory(facts: list[dict] | None = None) -> dict:
    return {
        "version": "1.0",
        "lastUpdated": "2026-03-26T12:00:00Z",
        "user": {
            "workContext": {"summary": "", "updatedAt": ""},
            "personalContext": {"summary": "", "updatedAt": ""},
            "topOfMind": {"summary": "", "updatedAt": ""},
        },
        "history": {
            "recentMonths": {"summary": "", "updatedAt": ""},
            "earlierContext": {"summary": "", "updatedAt": ""},
            "longTermBackground": {"summary": "", "updatedAt": ""},
        },
        "facts": facts or [],
    }


def _make_app(user_id: str | None = USER_A):
    """Create a test app with the memory router and optional auth override."""
    app = FastAPI()
    app.include_router(memory.router)
    if user_id is not None:
        async def _override() -> str:
            return user_id
        app.dependency_overrides[get_current_user_id] = _override
    return app


# ---------------------------------------------------------------------------
# US-008: Unauthenticated access returns 401
# ---------------------------------------------------------------------------


class TestMemoryAuthRequired:
    """All memory endpoints must return 401 when unauthenticated."""

    def test_get_memory_unauthenticated_returns_401(self):
        app = _make_app(user_id=None)
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.get("/api/memory")
        assert resp.status_code == 401

    def test_get_memory_status_unauthenticated_returns_401(self):
        app = _make_app(user_id=None)
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.get("/api/memory/status")
        assert resp.status_code == 401

    def test_reload_memory_unauthenticated_returns_401(self):
        app = _make_app(user_id=None)
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.post("/api/memory/reload")
        assert resp.status_code == 401

    def test_clear_memory_unauthenticated_returns_401(self):
        app = _make_app(user_id=None)
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.delete("/api/memory")
        assert resp.status_code == 401

    def test_export_memory_unauthenticated_returns_401(self):
        app = _make_app(user_id=None)
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.get("/api/memory/export")
        assert resp.status_code == 401

    def test_import_memory_unauthenticated_returns_401(self):
        app = _make_app(user_id=None)
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.post("/api/memory/import", json=_sample_memory())
        assert resp.status_code == 401

    def test_create_fact_unauthenticated_returns_401(self):
        app = _make_app(user_id=None)
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.post("/api/memory/facts", json={"content": "test"})
        assert resp.status_code == 401

    def test_delete_fact_unauthenticated_returns_401(self):
        app = _make_app(user_id=None)
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.delete("/api/memory/facts/fact-1")
        assert resp.status_code == 401

    def test_update_fact_unauthenticated_returns_401(self):
        app = _make_app(user_id=None)
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.patch("/api/memory/facts/fact-1", json={"content": "test"})
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# US-008: Per-user isolation — user A and user B see different memory
# ---------------------------------------------------------------------------


class TestMemoryPerUserIsolation:
    """User A and user B write different memory facts without cross-read."""

    def test_user_a_and_user_b_get_different_memory(self):
        """get_memory_data is called with the authenticated user's ID."""
        memory_a = _sample_memory(facts=[{"id": "f1", "content": "User A fact", "category": "context", "confidence": 0.9, "createdAt": "", "source": "manual"}])
        memory_b = _sample_memory(facts=[{"id": "f2", "content": "User B fact", "category": "context", "confidence": 0.9, "createdAt": "", "source": "manual"}])

        def _get_memory_data(user_id: str | None) -> dict:
            if user_id == USER_A:
                return memory_a
            if user_id == USER_B:
                return memory_b
            return _sample_memory()

        with patch("app.gateway.routers.memory.get_memory_data", side_effect=_get_memory_data):
            app_a = _make_app(user_id=USER_A)
            with TestClient(app_a, raise_server_exceptions=False) as client:
                resp_a = client.get("/api/memory")

            app_b = _make_app(user_id=USER_B)
            with TestClient(app_b, raise_server_exceptions=False) as client:
                resp_b = client.get("/api/memory")

        assert resp_a.status_code == 200
        assert resp_b.status_code == 200
        assert resp_a.json()["facts"][0]["content"] == "User A fact"
        assert resp_b.json()["facts"][0]["content"] == "User B fact"
        # Cross-read check: user A does not see user B's fact
        assert resp_a.json()["facts"][0]["id"] != resp_b.json()["facts"][0]["id"]

    def test_create_fact_passes_authenticated_user_id(self):
        """create_memory_fact is called with the authenticated user's ID."""
        app = _make_app(user_id=USER_A)
        updated_memory = _sample_memory()

        with patch("app.gateway.routers.memory.create_memory_fact", return_value=updated_memory) as mock_create:
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.post("/api/memory/facts", json={"content": "User A fact"})

        assert resp.status_code == 200
        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs.get("user_id") == USER_A

    def test_delete_fact_passes_authenticated_user_id(self):
        """delete_memory_fact is called with the authenticated user's ID."""
        app = _make_app(user_id=USER_B)
        updated_memory = _sample_memory()

        with patch("app.gateway.routers.memory.delete_memory_fact", return_value=updated_memory) as mock_delete:
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.delete("/api/memory/facts/fact-1")

        assert resp.status_code == 200
        mock_delete.assert_called_once_with("fact-1", USER_B)

    def test_memory_status_passes_authenticated_user_id(self):
        """get_memory_status uses the authenticated user's ID."""
        app = _make_app(user_id=USER_A)
        memory_a = _sample_memory()

        with patch("app.gateway.routers.memory.get_memory_data", return_value=memory_a) as mock_get:
            with patch("app.gateway.routers.memory.get_memory_config") as mock_cfg:
                mock_cfg.return_value.enabled = True
                mock_cfg.return_value.storage_path = ".deer-flow/memory.json"
                mock_cfg.return_value.debounce_seconds = 30
                mock_cfg.return_value.max_facts = 100
                mock_cfg.return_value.fact_confidence_threshold = 0.7
                mock_cfg.return_value.injection_enabled = True
                mock_cfg.return_value.max_injection_tokens = 2000
                with TestClient(app, raise_server_exceptions=False) as client:
                    resp = client.get("/api/memory/status")

        assert resp.status_code == 200
        mock_get.assert_called_once_with(USER_A)


# ---------------------------------------------------------------------------
# Existing functional tests (updated to use dependency_overrides)
# ---------------------------------------------------------------------------


def test_export_memory_route_returns_current_memory() -> None:
    app = _make_app()
    exported_memory = _sample_memory(
        facts=[
            {
                "id": "fact_export",
                "content": "User prefers concise responses.",
                "category": "preference",
                "confidence": 0.9,
                "createdAt": "2026-03-20T00:00:00Z",
                "source": "thread-1",
            }
        ]
    )

    with patch("app.gateway.routers.memory.get_memory_data", return_value=exported_memory):
        with TestClient(app) as client:
            response = client.get("/api/memory/export")

    assert response.status_code == 200
    assert response.json()["facts"] == exported_memory["facts"]


def test_import_memory_route_returns_imported_memory() -> None:
    app = _make_app()
    imported_memory = _sample_memory(
        facts=[
            {
                "id": "fact_import",
                "content": "User works on Scientific Tumbleweed.",
                "category": "context",
                "confidence": 0.87,
                "createdAt": "2026-03-20T00:00:00Z",
                "source": "manual",
            }
        ]
    )

    with patch("app.gateway.routers.memory.import_memory_data", return_value=imported_memory):
        with TestClient(app) as client:
            response = client.post("/api/memory/import", json=imported_memory)

    assert response.status_code == 200
    assert response.json()["facts"] == imported_memory["facts"]


def test_export_memory_route_preserves_source_error() -> None:
    app = _make_app()
    exported_memory = _sample_memory(
        facts=[
            {
                "id": "fact_correction",
                "content": "Use make dev for local development.",
                "category": "correction",
                "confidence": 0.95,
                "createdAt": "2026-03-20T00:00:00Z",
                "source": "thread-1",
                "sourceError": "The agent previously suggested npm start.",
            }
        ]
    )

    with patch("app.gateway.routers.memory.get_memory_data", return_value=exported_memory):
        with TestClient(app) as client:
            response = client.get("/api/memory/export")

    assert response.status_code == 200
    assert response.json()["facts"][0]["sourceError"] == "The agent previously suggested npm start."


def test_import_memory_route_preserves_source_error() -> None:
    app = _make_app()
    imported_memory = _sample_memory(
        facts=[
            {
                "id": "fact_correction",
                "content": "Use make dev for local development.",
                "category": "correction",
                "confidence": 0.95,
                "createdAt": "2026-03-20T00:00:00Z",
                "source": "thread-1",
                "sourceError": "The agent previously suggested npm start.",
            }
        ]
    )

    with patch("app.gateway.routers.memory.import_memory_data", return_value=imported_memory):
        with TestClient(app) as client:
            response = client.post("/api/memory/import", json=imported_memory)

    assert response.status_code == 200
    assert response.json()["facts"][0]["sourceError"] == "The agent previously suggested npm start."


def test_clear_memory_route_returns_cleared_memory() -> None:
    app = _make_app()

    with patch("app.gateway.routers.memory.clear_memory_data", return_value=_sample_memory()):
        with TestClient(app) as client:
            response = client.delete("/api/memory")

    assert response.status_code == 200
    assert response.json()["facts"] == []


def test_create_memory_fact_route_returns_updated_memory() -> None:
    app = _make_app()
    updated_memory = _sample_memory(
        facts=[
            {
                "id": "fact_new",
                "content": "User prefers concise code reviews.",
                "category": "preference",
                "confidence": 0.88,
                "createdAt": "2026-03-20T00:00:00Z",
                "source": "manual",
            }
        ]
    )

    with patch("app.gateway.routers.memory.create_memory_fact", return_value=updated_memory):
        with TestClient(app) as client:
            response = client.post(
                "/api/memory/facts",
                json={
                    "content": "User prefers concise code reviews.",
                    "category": "preference",
                    "confidence": 0.88,
                },
            )

    assert response.status_code == 200
    assert response.json()["facts"] == updated_memory["facts"]


def test_delete_memory_fact_route_returns_updated_memory() -> None:
    app = _make_app()
    updated_memory = _sample_memory(
        facts=[
            {
                "id": "fact_keep",
                "content": "User likes Python",
                "category": "preference",
                "confidence": 0.9,
                "createdAt": "2026-03-20T00:00:00Z",
                "source": "thread-1",
            }
        ]
    )

    with patch("app.gateway.routers.memory.delete_memory_fact", return_value=updated_memory):
        with TestClient(app) as client:
            response = client.delete("/api/memory/facts/fact_delete")

    assert response.status_code == 200
    assert response.json()["facts"] == updated_memory["facts"]


def test_delete_memory_fact_route_returns_404_for_missing_fact() -> None:
    app = _make_app()

    with patch("app.gateway.routers.memory.delete_memory_fact", side_effect=KeyError("fact_missing")):
        with TestClient(app) as client:
            response = client.delete("/api/memory/facts/fact_missing")

    assert response.status_code == 404
    assert response.json()["detail"] == "Memory fact 'fact_missing' not found."


def test_update_memory_fact_route_returns_updated_memory() -> None:
    app = _make_app()
    updated_memory = _sample_memory(
        facts=[
            {
                "id": "fact_edit",
                "content": "User prefers spaces",
                "category": "workflow",
                "confidence": 0.91,
                "createdAt": "2026-03-20T00:00:00Z",
                "source": "manual",
            }
        ]
    )

    with patch("app.gateway.routers.memory.update_memory_fact", return_value=updated_memory):
        with TestClient(app) as client:
            response = client.patch(
                "/api/memory/facts/fact_edit",
                json={
                    "content": "User prefers spaces",
                    "category": "workflow",
                    "confidence": 0.91,
                },
            )

    assert response.status_code == 200
    assert response.json()["facts"] == updated_memory["facts"]


def test_update_memory_fact_route_preserves_omitted_fields() -> None:
    app = _make_app()
    updated_memory = _sample_memory(
        facts=[
            {
                "id": "fact_edit",
                "content": "User prefers spaces",
                "category": "preference",
                "confidence": 0.8,
                "createdAt": "2026-03-20T00:00:00Z",
                "source": "manual",
            }
        ]
    )

    with patch("app.gateway.routers.memory.update_memory_fact", return_value=updated_memory) as update_fact:
        with TestClient(app) as client:
            response = client.patch(
                "/api/memory/facts/fact_edit",
                json={
                    "content": "User prefers spaces",
                },
            )

    assert response.status_code == 200
    update_fact.assert_called_once_with(
        fact_id="fact_edit",
        content="User prefers spaces",
        category=None,
        confidence=None,
        user_id=USER_A,
    )
    assert response.json()["facts"] == updated_memory["facts"]


def test_update_memory_fact_route_returns_404_for_missing_fact() -> None:
    app = _make_app()

    with patch("app.gateway.routers.memory.update_memory_fact", side_effect=KeyError("fact_missing")):
        with TestClient(app) as client:
            response = client.patch(
                "/api/memory/facts/fact_missing",
                json={
                    "content": "User prefers spaces",
                    "category": "workflow",
                    "confidence": 0.91,
                },
            )

    assert response.status_code == 404
    assert response.json()["detail"] == "Memory fact 'fact_missing' not found."


def test_update_memory_fact_route_returns_specific_error_for_invalid_confidence() -> None:
    app = _make_app()

    with patch("app.gateway.routers.memory.update_memory_fact", side_effect=ValueError("confidence")):
        with TestClient(app) as client:
            response = client.patch(
                "/api/memory/facts/fact_edit",
                json={
                    "content": "User prefers spaces",
                    "confidence": 0.91,
                },
            )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid confidence value; must be between 0 and 1."
