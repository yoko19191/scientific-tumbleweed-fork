"""Tests for the sandbox capacity gateway API."""

from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.gateway.routers import sandbox as sandbox_router


def test_capacity_endpoint_returns_provider_capacity():
    app = FastAPI()
    app.include_router(sandbox_router.router)

    provider = MagicMock()
    provider.get_capacity.return_value = {
        "enabled": True,
        "backend": "local",
        "limit": 10,
        "active": 8,
        "warm": 1,
        "total": 9,
        "available": 1,
        "saturated": False,
    }

    with patch.object(sandbox_router, "get_sandbox_provider", return_value=provider):
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/api/sandbox/capacity")

    assert response.status_code == 200
    assert response.json()["limit"] == 10
    assert response.json()["available"] == 1


def test_capacity_endpoint_disables_unknown_provider():
    app = FastAPI()
    app.include_router(sandbox_router.router)

    with patch.object(sandbox_router, "get_sandbox_provider", return_value=object()):
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/api/sandbox/capacity")

    assert response.status_code == 200
    assert response.json() == {
        "enabled": False,
        "backend": "unknown",
        "limit": None,
        "active": 0,
        "warm": 0,
        "total": 0,
        "available": None,
        "saturated": False,
    }
