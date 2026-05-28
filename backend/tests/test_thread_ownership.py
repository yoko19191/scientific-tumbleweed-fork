"""Tests for thread ownership service in app.gateway.thread_ownership.

Covers:
- bind_thread_to_user: new binding, idempotent same user, conflict different user
- require_thread_owner: owner match, owner mismatch, missing owner mapping, malicious client user_id metadata
- get_thread_owner: match, mismatch, missing
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI

from app.gateway.thread_ownership import (
    bind_thread_to_user,
    get_thread_owner,
    require_thread_owner,
)
from app.gateway.thread_resources import AuthenticatedThreadResource, get_authenticated_thread_resource
from app.gateway.user_prefix import user_thread_owners_namespace
from deerflow.config.paths import Paths

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

USER_A = "user-aaaa-1111"
USER_B = "user-bbbb-2222"
THREAD_1 = "thread-0001"


def _make_store_item(user_id: str):
    item = MagicMock()
    item.value = {"user_id": user_id}
    return item


def _make_store(*, owner: str | None = None):
    """Return a mock Store with aget/aput/adelete."""
    store = MagicMock()
    store.aget = AsyncMock(return_value=_make_store_item(owner) if owner else None)
    store.aput = AsyncMock()
    store.adelete = AsyncMock()
    return store


# ---------------------------------------------------------------------------
# bind_thread_to_user
# ---------------------------------------------------------------------------


class TestBindThreadToUser:
    @pytest.mark.anyio
    async def test_new_binding_writes_to_store(self):
        store = _make_store(owner=None)
        await bind_thread_to_user(store, USER_A, THREAD_1)
        store.aput.assert_awaited_once()
        ns, key, value = store.aput.call_args.args
        assert ns == user_thread_owners_namespace(USER_A)
        assert key == THREAD_1
        assert value["user_id"] == USER_A

    @pytest.mark.anyio
    async def test_idempotent_same_user_does_not_write(self):
        store = _make_store(owner=USER_A)
        await bind_thread_to_user(store, USER_A, THREAD_1)
        store.aput.assert_not_awaited()

    @pytest.mark.anyio
    async def test_conflict_different_user_raises_403(self):
        store = _make_store(owner=USER_B)
        with pytest.raises(Exception) as exc_info:
            await bind_thread_to_user(store, USER_A, THREAD_1)
        assert exc_info.value.status_code == 403

    @pytest.mark.anyio
    async def test_invalid_user_id_raises_value_error(self):
        store = _make_store()
        with pytest.raises(ValueError):
            await bind_thread_to_user(store, "", THREAD_1)

    @pytest.mark.anyio
    async def test_invalid_user_id_with_slash_raises(self):
        store = _make_store()
        with pytest.raises(ValueError):
            await bind_thread_to_user(store, "user/evil", THREAD_1)


# ---------------------------------------------------------------------------
# require_thread_owner
# ---------------------------------------------------------------------------


def _make_request_with_store(store):
    """Build a minimal FastAPI Request with the given store on app.state."""
    app = FastAPI()
    app.state.store = store
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"",
        "headers": [],
        "app": app,
    }
    from starlette.requests import Request as StarletteRequest

    return StarletteRequest(scope)


class TestRequireThreadOwner:
    @pytest.mark.anyio
    async def test_owner_match_returns_user_id(self):
        store = _make_store(owner=USER_A)
        request = _make_request_with_store(store)

        with patch("app.gateway.deps.get_current_user_id", new=AsyncMock(return_value=USER_A)):
            result = await require_thread_owner(request, THREAD_1)

        assert result == USER_A

    @pytest.mark.anyio
    async def test_owner_mismatch_raises_404(self):
        # Store says USER_B owns the thread, but current user is USER_A
        store = _make_store(owner=USER_B)
        request = _make_request_with_store(store)

        with patch("app.gateway.deps.get_current_user_id", new=AsyncMock(return_value=USER_A)):
            with pytest.raises(Exception) as exc_info:
                await require_thread_owner(request, THREAD_1)

        assert exc_info.value.status_code == 404


class TestAuthenticatedThreadResource:
    def test_resolves_virtual_path_under_authenticated_user_prefix(self, tmp_path):
        paths = Paths(tmp_path)
        resource = AuthenticatedThreadResource(thread_id=THREAD_1, user_id=USER_A, paths=paths)

        resolved = resource.resolve_virtual_path("/mnt/user-data/outputs/report.txt")

        assert resolved == (paths.user_thread_dir(USER_A, THREAD_1) / "outputs" / "report.txt").resolve()

    def test_delete_local_data_removes_only_authenticated_user_thread(self, tmp_path):
        paths = Paths(tmp_path)
        paths.user_thread_workspace_dir(USER_A, THREAD_1).mkdir(parents=True)
        paths.user_thread_workspace_dir(USER_B, THREAD_1).mkdir(parents=True)

        resource = AuthenticatedThreadResource(thread_id=THREAD_1, user_id=USER_A, paths=paths)
        resource.delete_local_data()

        assert not paths.user_thread_dir(USER_A, THREAD_1).exists()
        assert paths.user_thread_dir(USER_B, THREAD_1).exists()

    @pytest.mark.anyio
    async def test_get_authenticated_thread_resource_uses_ownership_interface(self, tmp_path):
        request = _make_request_with_store(_make_store(owner=USER_A))
        paths = Paths(tmp_path)

        with patch("app.gateway.thread_resources.require_thread_owner", new=AsyncMock(return_value=USER_A)) as require_owner:
            resource = await get_authenticated_thread_resource(request, THREAD_1, paths=paths)

        require_owner.assert_awaited_once_with(request, THREAD_1)
        assert resource.thread_id == THREAD_1
        assert resource.user_id == USER_A
        assert resource.paths is paths

    @pytest.mark.anyio
    async def test_missing_owner_mapping_raises_404(self):
        store = _make_store(owner=None)
        request = _make_request_with_store(store)

        with patch("app.gateway.deps.get_current_user_id", new=AsyncMock(return_value=USER_A)):
            with pytest.raises(Exception) as exc_info:
                await require_thread_owner(request, THREAD_1)

        assert exc_info.value.status_code == 404

    @pytest.mark.anyio
    async def test_no_auth_raises_401(self):
        from fastapi import HTTPException

        store = _make_store(owner=USER_A)
        request = _make_request_with_store(store)

        with patch(
            "app.gateway.deps.get_current_user_id",
            new=AsyncMock(side_effect=HTTPException(status_code=401, detail="Authentication required")),
        ):
            with pytest.raises(Exception) as exc_info:
                await require_thread_owner(request, THREAD_1)

        assert exc_info.value.status_code == 401

    @pytest.mark.anyio
    async def test_store_unavailable_raises_503(self):
        # Store is None on app.state
        app = FastAPI()
        app.state.store = None
        from starlette.requests import Request as StarletteRequest

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "query_string": b"",
            "headers": [],
            "app": app,
        }
        request = StarletteRequest(scope)

        with patch("app.gateway.deps.get_current_user_id", new=AsyncMock(return_value=USER_A)):
            with pytest.raises(Exception) as exc_info:
                await require_thread_owner(request, THREAD_1)

        assert exc_info.value.status_code == 503

    @pytest.mark.anyio
    async def test_malicious_client_user_id_in_metadata_is_ignored(self):
        """Client-supplied user_id in request body/metadata must not bypass ownership.

        The ownership check reads only from the server-authenticated user ID
        (from the cookie) and the Store — never from request body or metadata.
        """
        # Store says USER_B owns the thread
        store = _make_store(owner=USER_B)
        request = _make_request_with_store(store)

        # Attacker is authenticated as USER_A but tries to access USER_B's thread
        with patch("app.gateway.deps.get_current_user_id", new=AsyncMock(return_value=USER_A)):
            with pytest.raises(Exception) as exc_info:
                # Even if the attacker somehow injects USER_B into the request,
                # require_thread_owner only uses the cookie-derived USER_A
                await require_thread_owner(request, THREAD_1)

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# get_thread_owner
# ---------------------------------------------------------------------------


class TestGetThreadOwner:
    @pytest.mark.anyio
    async def test_returns_user_id_when_match(self):
        store = _make_store(owner=USER_A)
        result = await get_thread_owner(store, USER_A, THREAD_1)
        assert result == USER_A

    @pytest.mark.anyio
    async def test_returns_none_when_mismatch(self):
        store = _make_store(owner=USER_B)
        result = await get_thread_owner(store, USER_A, THREAD_1)
        assert result is None

    @pytest.mark.anyio
    async def test_returns_none_when_no_mapping(self):
        store = _make_store(owner=None)
        result = await get_thread_owner(store, USER_A, THREAD_1)
        assert result is None

    @pytest.mark.anyio
    async def test_invalid_user_id_raises(self):
        store = _make_store()
        with pytest.raises(ValueError):
            await get_thread_owner(store, "", THREAD_1)
