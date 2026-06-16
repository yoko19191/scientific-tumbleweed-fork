"""Regression tests for Gateway lifespan shutdown.

These tests guard the invariant that lifespan shutdown is *bounded*: a
misbehaving channel whose ``stop()`` blocks forever must not keep the
uvicorn worker alive. A hung worker is the precondition for the
signal-reentrancy deadlock described in
``app.gateway.app._SHUTDOWN_HOOK_TIMEOUT_SECONDS``.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import FastAPI


@asynccontextmanager
async def _noop_langgraph_runtime(_app, _startup_config):
    yield


async def _run_lifespan_with_hanging_stop() -> float:
    """Drive the lifespan context with stop_channel_service hanging forever.

    Returns the elapsed wall-clock seconds.
    """
    from app.gateway.app import _SHUTDOWN_HOOK_TIMEOUT_SECONDS, lifespan

    async def hang_forever() -> None:
        await asyncio.sleep(3600)

    app = FastAPI()

    fake_service = MagicMock()
    fake_service.get_status = MagicMock(return_value={})

    async def fake_start():
        return fake_service

    async def noop_async(*_args, **_kwargs):
        return None

    with (
        patch("app.gateway.app.get_app_config", return_value=SimpleNamespace(memory=SimpleNamespace(token_counting="char"), log_level="info")),
        patch("app.gateway.app.get_gateway_config", return_value=MagicMock(host="x", port=0)),
        patch("app.gateway.app.langgraph_runtime", _noop_langgraph_runtime),
        patch("deerflow.db.init_engine", side_effect=noop_async),
        patch("deerflow.db.ensure_schema", side_effect=noop_async),
        patch("deerflow.db.init_pool", side_effect=noop_async),
        patch("deerflow.db.close_pool", side_effect=noop_async),
        patch("deerflow.db.close_engine", side_effect=noop_async),
        patch("deerflow.db.init_sync_engine"),
        patch("deerflow.db.close_sync_engine"),
        patch("app.channels.service.start_channel_service", side_effect=fake_start),
        patch("app.channels.service.stop_channel_service", side_effect=hang_forever),
    ):
        loop = asyncio.get_event_loop()
        start = loop.time()
        async with lifespan(app):
            pass
        elapsed = loop.time() - start

    assert _SHUTDOWN_HOOK_TIMEOUT_SECONDS < 30.0, "Timeout constant must stay modest"
    return elapsed


def test_shutdown_is_bounded_when_channel_stop_hangs():
    """Lifespan exit must complete near the configured timeout, not hang."""
    from app.gateway.app import _SHUTDOWN_HOOK_TIMEOUT_SECONDS

    elapsed = asyncio.run(_run_lifespan_with_hanging_stop())

    # Generous upper bound: timeout + 2s slack for scheduling overhead.
    assert elapsed < _SHUTDOWN_HOOK_TIMEOUT_SECONDS + 2.0, f"Lifespan shutdown took {elapsed:.2f}s; expected <= {_SHUTDOWN_HOOK_TIMEOUT_SECONDS + 2.0:.1f}s"
    # Lower bound: the wait_for should actually have waited.
    assert elapsed >= _SHUTDOWN_HOOK_TIMEOUT_SECONDS - 0.5, f"Lifespan exited too quickly ({elapsed:.2f}s); wait_for may not have been invoked."


def _runtime_context(events: list[str], name: str, value=None):
    @asynccontextmanager
    async def _context(*_args, **_kwargs):
        events.append(f"{name}:enter")
        try:
            yield value
        finally:
            events.append(f"{name}:exit")

    return _context


async def _run_langgraph_runtime_shutdown_order() -> list[str]:
    from app.gateway import deps

    events: list[str] = []

    class FakeRunManager:
        def __init__(self, *, store):
            self.store = store
            events.append("run-manager:init")

        async def shutdown(self, *, timeout: float) -> list[str]:
            events.append("run-manager:shutdown")
            assert timeout == deps._RUN_MANAGER_SHUTDOWN_TIMEOUT_SECONDS
            assert "store:exit" not in events
            assert "checkpointer:exit" not in events
            assert "stream:exit" not in events
            return ["run-1"]

    stream_context = _runtime_context(events, "stream", object())
    checkpointer_context = _runtime_context(events, "checkpointer", object())
    store_context = _runtime_context(events, "store", None)

    app = FastAPI()
    startup_config = SimpleNamespace(stream_bridge=SimpleNamespace())

    with (
        patch("deerflow.runtime.make_stream_bridge", side_effect=lambda *_args, **_kwargs: stream_context()),
        patch(
            "deerflow.agents.checkpointer.async_provider.make_checkpointer",
            side_effect=lambda *_args, **_kwargs: checkpointer_context(),
        ),
        patch("deerflow.runtime.make_store", side_effect=lambda *_args, **_kwargs: store_context()),
        patch("app.gateway.deps.RunManager", FakeRunManager),
    ):
        async with deps.langgraph_runtime(app, startup_config):
            events.append("inside")

    return events


def test_langgraph_runtime_drains_run_manager_before_runtime_resources_exit():
    """Run shutdown must happen before checkpointer/store contexts close."""
    events = asyncio.run(_run_langgraph_runtime_shutdown_order())

    assert events.index("run-manager:shutdown") < events.index("store:exit")
    assert events.index("run-manager:shutdown") < events.index("checkpointer:exit")
    assert events.index("run-manager:shutdown") < events.index("stream:exit")
