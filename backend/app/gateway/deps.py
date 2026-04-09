"""Centralized accessors for singleton objects stored on ``app.state``.

**Getters** (used by routers): raise 503 when a required dependency is
missing, except ``get_store`` which returns ``None``.

Initialization is handled directly in ``app.py`` via :class:`AsyncExitStack`.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import AsyncExitStack, asynccontextmanager

from fastapi import FastAPI, HTTPException, Request

from deerflow.runtime import RunManager, StreamBridge


@asynccontextmanager
async def langgraph_runtime(app: FastAPI) -> AsyncGenerator[None, None]:
    """Bootstrap and tear down all LangGraph runtime singletons.

    Usage in ``app.py``::

        async with langgraph_runtime(app):
            yield
    """
    from deerflow.agents.checkpointer.async_provider import make_checkpointer
    from deerflow.runtime import make_store, make_stream_bridge

    async with AsyncExitStack() as stack:
        app.state.stream_bridge = await stack.enter_async_context(make_stream_bridge())
        app.state.checkpointer = await stack.enter_async_context(make_checkpointer())
        app.state.store = await stack.enter_async_context(make_store())
        app.state.run_manager = RunManager()
        yield


# ---------------------------------------------------------------------------
# Getters – called by routers per-request
# ---------------------------------------------------------------------------


def get_stream_bridge(request: Request) -> StreamBridge:
    """Return the global :class:`StreamBridge`, or 503."""
    bridge = getattr(request.app.state, "stream_bridge", None)
    if bridge is None:
        raise HTTPException(status_code=503, detail="Stream bridge not available")
    return bridge


def get_run_manager(request: Request) -> RunManager:
    """Return the global :class:`RunManager`, or 503."""
    mgr = getattr(request.app.state, "run_manager", None)
    if mgr is None:
        raise HTTPException(status_code=503, detail="Run manager not available")
    return mgr


def get_checkpointer(request: Request):
    """Return the global checkpointer, or 503."""
    cp = getattr(request.app.state, "checkpointer", None)
    if cp is None:
        raise HTTPException(status_code=503, detail="Checkpointer not available")
    return cp


def get_store(request: Request):
    """Return the global store (may be ``None`` if not configured)."""
    return getattr(request.app.state, "store", None)


# ---------------------------------------------------------------------------
# Auth helpers – bridge between auth module and resource routers
# ---------------------------------------------------------------------------


def get_optional_user_id(request: Request) -> str | None:
    """Extract the authenticated user's ID from the request, or ``None``.

    Works with the RFC-001 auth module (``request.state.auth.user.id``)
    when it is active.  Returns ``None`` when auth is not enabled or the
    request is anonymous — callers fall back to global (non-isolated) paths.
    """
    auth = getattr(request.state, "auth", None)
    if auth is None:
        return None
    user = getattr(auth, "user", None)
    if user is None:
        return None
    uid = getattr(user, "id", None)
    return str(uid) if uid is not None else None


def get_auth_provider(request: Request):
    """Return the :class:`LocalAuthProvider` singleton, or 503."""
    provider = getattr(request.app.state, "auth_provider", None)
    if provider is None:
        raise HTTPException(status_code=503, detail="Auth provider not available")
    return provider


def get_user_repo(request: Request):
    """Return the :class:`SQLiteUserRepository` singleton, or 503."""
    repo = getattr(request.app.state, "user_repo", None)
    if repo is None:
        raise HTTPException(status_code=503, detail="User repository not available")
    return repo


def get_auth_config(request: Request):
    """Return the :class:`AuthConfig` singleton, or 503."""
    cfg = getattr(request.app.state, "auth_config", None)
    if cfg is None:
        raise HTTPException(status_code=503, detail="Auth config not available")
    return cfg


# ---------------------------------------------------------------------------
# User resolution from JWT cookie
# ---------------------------------------------------------------------------


def get_local_provider() -> "LocalAuthProvider":
    """Return the global :class:`LocalAuthProvider`.

    Called as a plain function (not per-request) by ``routers/auth.py``
    because the provider is a process-level singleton set during lifespan.
    """
    from app.gateway.auth.local_provider import LocalAuthProvider

    # Import here to avoid circular imports at module level.
    # The provider is stored on the app state during lifespan init.
    # We access it via the module-level _auth_provider cache.
    global _local_provider
    if _local_provider is not None:
        return _local_provider
    raise RuntimeError("LocalAuthProvider not initialised — lifespan not started?")


_local_provider: "LocalAuthProvider | None" = None


def set_local_provider(provider: "LocalAuthProvider") -> None:
    """Called once from lifespan to cache the provider at module level."""
    global _local_provider
    _local_provider = provider


async def get_optional_user_from_request(request: Request):
    """Decode the JWT cookie and return the :class:`User`, or ``None``.

    This is the full JWT → User pipeline used by ``authz.py``.
    Returns ``None`` when no cookie is present or the token is invalid.
    """
    from app.gateway.auth.errors import TokenError
    from app.gateway.auth.jwt import decode_token

    cookie_value = request.cookies.get("access_token")
    if not cookie_value:
        return None

    result = decode_token(cookie_value)
    if isinstance(result, TokenError):
        return None

    provider = get_local_provider()
    user = await provider.get_user_by_id(result.sub)
    if user is None:
        return None

    # Verify token_version matches (password-change invalidation)
    if user.token_version != result.ver:
        return None

    return user


async def get_current_user_from_request(request: Request):
    """Like :func:`get_optional_user_from_request` but raises 401 if absent."""
    user = await get_optional_user_from_request(request)
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user
