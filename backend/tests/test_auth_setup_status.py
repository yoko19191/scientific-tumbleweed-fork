"""Tests for setup-status cache behavior."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from app.gateway.routers import auth as auth_router


class _FakeProvider:
    def __init__(self, *, users: int) -> None:
        self.users = users
        self.calls = 0

    async def count_users(self) -> int:
        self.calls += 1
        return self.users


def _request(ip: str = "127.0.0.1"):
    return SimpleNamespace(headers={}, client=SimpleNamespace(host=ip))


@pytest.fixture(autouse=True)
def _clear_setup_status_state():
    auth_router._SETUP_STATUS_CACHE.clear()
    auth_router._SETUP_STATUS_INFLIGHT.clear()
    yield
    auth_router._SETUP_STATUS_CACHE.clear()
    auth_router._SETUP_STATUS_INFLIGHT.clear()


@pytest.mark.anyio
async def test_setup_status_returns_cached_initialized_result(monkeypatch):
    provider = _FakeProvider(users=1)
    monkeypatch.setattr(auth_router, "get_local_provider", lambda: provider)

    first = await auth_router.setup_status(_request())
    second = await auth_router.setup_status(_request())

    assert first == {"needs_setup": False}
    assert second == {"needs_setup": False}
    assert provider.calls == 1


@pytest.mark.anyio
async def test_setup_status_reuses_inflight_lookup(monkeypatch):
    started = asyncio.Event()
    release = asyncio.Event()

    class SlowProvider(_FakeProvider):
        async def count_users(self) -> int:
            self.calls += 1
            started.set()
            await release.wait()
            return self.users

    provider = SlowProvider(users=1)
    monkeypatch.setattr(auth_router, "get_local_provider", lambda: provider)

    first = asyncio.create_task(auth_router.setup_status(_request("10.0.0.1")))
    await started.wait()
    second = asyncio.create_task(auth_router.setup_status(_request("10.0.0.1")))
    release.set()

    assert await first == {"needs_setup": False}
    assert await second == {"needs_setup": False}
    assert provider.calls == 1
