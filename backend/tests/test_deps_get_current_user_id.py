"""Tests for get_current_user_id dependency in app.gateway.deps.

Covers:
- Valid cookie → returns user ID string
- Missing cookie → 401
- Invalid/malformed token → 401
- Expired token → 401
- Unknown user (not in repo) → 401
- token_version mismatch → 401
- get_optional_user_id still works for legacy/optional paths
"""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware

from app.gateway.deps import get_current_user_id, get_optional_user_id

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_USER_ID = UUID("12345678-1234-5678-1234-567812345678")
_USER_ID_STR = str(_USER_ID)


def _make_user(token_version: int = 0):
    user = MagicMock()
    user.id = _USER_ID
    user.token_version = token_version
    return user


def _make_token_payload(sub: str = _USER_ID_STR, ver: int = 0):
    payload = MagicMock()
    payload.sub = sub
    payload.ver = ver
    return payload


def _build_test_app():
    app = FastAPI()

    @app.get("/test")
    async def _route(user_id: str = Depends(get_current_user_id)):
        return {"user_id": user_id}

    return app


@contextmanager
def _make_client(*, cookie: str | None, token_payload=None, user=None):
    """Build a TestClient with mocked auth internals."""
    from app.gateway.auth.errors import TokenError

    app = _build_test_app()

    def _decode(token):
        if token_payload is None:
            return TokenError.MALFORMED
        return token_payload

    provider_mock = MagicMock()
    provider_mock.get_user = AsyncMock(return_value=user)

    with (
        patch("app.gateway.deps.get_local_provider", return_value=provider_mock),
        patch("app.gateway.auth.jwt.decode_token", side_effect=_decode),
    ):
        client = TestClient(app, raise_server_exceptions=False)
        if cookie is not None:
            client.cookies.set("access_token", cookie)
        yield client


# ---------------------------------------------------------------------------
# get_current_user_id tests
# ---------------------------------------------------------------------------


def test_valid_cookie_returns_user_id():
    payload = _make_token_payload(ver=0)
    user = _make_user(token_version=0)
    with _make_client(cookie="valid.jwt.token", token_payload=payload, user=user) as client:
        resp = client.get("/test")
    assert resp.status_code == 200
    assert resp.json()["user_id"] == _USER_ID_STR


def test_missing_cookie_returns_401():
    with _make_client(cookie=None) as client:
        resp = client.get("/test")
    assert resp.status_code == 401


def test_malformed_token_returns_401():
    # token_payload=None → decode returns TokenError.MALFORMED
    with _make_client(cookie="bad.token", token_payload=None) as client:
        resp = client.get("/test")
    assert resp.status_code == 401


def test_expired_token_returns_401():
    from app.gateway.auth.errors import TokenError

    app = _build_test_app()
    provider_mock = MagicMock()
    provider_mock.get_user = AsyncMock(return_value=None)

    with (
        patch("app.gateway.deps.get_local_provider", return_value=provider_mock),
        patch("app.gateway.auth.jwt.decode_token", return_value=TokenError.EXPIRED),
    ):
        client = TestClient(app, raise_server_exceptions=False)
        client.cookies.set("access_token", "expired.token")
        resp = client.get("/test")
    assert resp.status_code == 401


def test_unknown_user_returns_401():
    payload = _make_token_payload(ver=0)
    # user=None → provider returns no user
    with _make_client(cookie="valid.jwt.token", token_payload=payload, user=None) as client:
        resp = client.get("/test")
    assert resp.status_code == 401


def test_token_version_mismatch_returns_401():
    payload = _make_token_payload(ver=1)
    user = _make_user(token_version=0)  # stored version differs from token
    with _make_client(cookie="valid.jwt.token", token_payload=payload, user=user) as client:
        resp = client.get("/test")
    assert resp.status_code == 401


def test_returns_string_not_uuid():
    payload = _make_token_payload(ver=0)
    user = _make_user(token_version=0)
    with _make_client(cookie="valid.jwt.token", token_payload=payload, user=user) as client:
        resp = client.get("/test")
    assert resp.status_code == 200
    result = resp.json()["user_id"]
    assert isinstance(result, str)
    assert result == _USER_ID_STR


def test_does_not_read_user_id_from_query_params():
    """user_id in query string must not be used — only cookie matters."""
    with _make_client(cookie=None) as client:
        resp = client.get("/test?user_id=some-user-id")
    assert resp.status_code == 401


def test_does_not_read_user_id_from_headers():
    """user_id in custom header must not be used — only cookie matters."""
    with _make_client(cookie=None) as client:
        resp = client.get("/test", headers={"X-User-Id": "some-user-id"})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# get_optional_user_id still works (legacy / optional paths)
# ---------------------------------------------------------------------------


def test_optional_user_id_returns_none_when_no_auth_state():
    """Without auth middleware, get_optional_user_id returns None."""
    app = FastAPI()

    @app.get("/test")
    async def _route(uid=Depends(get_optional_user_id)):
        return {"user_id": uid}

    client = TestClient(app)
    resp = client.get("/test")
    assert resp.status_code == 200
    assert resp.json()["user_id"] is None


def test_optional_user_id_returns_user_id_when_auth_state_present():
    """When request.state.auth.user.id is set, returns the ID."""
    app = FastAPI()

    class _InjectAuth(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            auth = MagicMock()
            auth.user = MagicMock()
            auth.user.id = _USER_ID
            request.state.auth = auth
            return await call_next(request)

    app.add_middleware(_InjectAuth)

    @app.get("/test")
    async def _route(uid=Depends(get_optional_user_id)):
        return {"user_id": uid}

    client = TestClient(app)
    resp = client.get("/test")
    assert resp.status_code == 200
    assert resp.json()["user_id"] == _USER_ID_STR
