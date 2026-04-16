"""Tests for US-011: Sandbox and thread-data middleware user-prefixed paths.

Verifies that:
- ThreadDataMiddleware uses trusted user_id when creating workspace/uploads/outputs paths
- Sandbox provider _get_thread_mounts uses user-prefixed host paths when user_id is given
- Same thread_id under two users produces distinct sandbox mount sources
- Sandbox acquire uses user-prefixed cache key so two users with same thread_id get distinct sandboxes
"""

import importlib
from unittest.mock import MagicMock, patch

from langgraph.runtime import Runtime

from deerflow.agents.middlewares.thread_data_middleware import ThreadDataMiddleware
from deerflow.config.paths import Paths

USER_A = "user-aaaa-1111"
USER_B = "user-bbbb-2222"
THREAD_ID = "thread-abc123"


def _as_posix(path: str) -> str:
    return path.replace("\\", "/")


# ---------------------------------------------------------------------------
# ThreadDataMiddleware: user-prefixed paths
# ---------------------------------------------------------------------------


class TestThreadDataMiddlewareUserPrefixed:
    """ThreadDataMiddleware uses trusted user_id for workspace/uploads/outputs paths."""

    def test_before_agent_uses_user_prefixed_paths_from_context(self, tmp_path):
        middleware = ThreadDataMiddleware(base_dir=str(tmp_path), lazy_init=True)
        runtime = Runtime(context={"thread_id": THREAD_ID, "user_id": USER_A})

        result = middleware.before_agent(state={}, runtime=runtime)

        assert result is not None
        assert USER_A in _as_posix(result["thread_data"]["workspace_path"])
        assert USER_A in _as_posix(result["thread_data"]["uploads_path"])
        assert USER_A in _as_posix(result["thread_data"]["outputs_path"])

    def test_before_agent_user_a_and_user_b_get_different_paths(self, tmp_path):
        middleware = ThreadDataMiddleware(base_dir=str(tmp_path), lazy_init=True)

        result_a = middleware.before_agent(
            state={}, runtime=Runtime(context={"thread_id": THREAD_ID, "user_id": USER_A})
        )
        result_b = middleware.before_agent(
            state={}, runtime=Runtime(context={"thread_id": THREAD_ID, "user_id": USER_B})
        )

        assert result_a is not None
        assert result_b is not None
        assert result_a["thread_data"]["workspace_path"] != result_b["thread_data"]["workspace_path"]
        assert USER_A in _as_posix(result_a["thread_data"]["workspace_path"])
        assert USER_B in _as_posix(result_b["thread_data"]["workspace_path"])

    def test_before_agent_uses_user_id_from_metadata(self, tmp_path, monkeypatch):
        middleware = ThreadDataMiddleware(base_dir=str(tmp_path), lazy_init=True)
        runtime = Runtime(context={"thread_id": THREAD_ID})

        monkeypatch.setattr(
            "deerflow.agents.middlewares.thread_data_middleware.get_config",
            lambda: {"configurable": {"thread_id": THREAD_ID}, "metadata": {"user_id": USER_A}},
        )

        result = middleware.before_agent(state={}, runtime=runtime)

        assert result is not None
        assert USER_A in _as_posix(result["thread_data"]["workspace_path"])


# ---------------------------------------------------------------------------
# Sandbox provider: user-prefixed mounts
# ---------------------------------------------------------------------------


class TestSandboxProviderUserPrefixedMounts:
    """_get_thread_mounts uses user-prefixed host paths when user_id is given."""

    def test_get_thread_mounts_uses_user_prefixed_paths(self, tmp_path, monkeypatch):
        aio_mod = importlib.import_module("deerflow.community.aio_sandbox.aio_sandbox_provider")
        monkeypatch.setattr(aio_mod, "get_paths", lambda: Paths(base_dir=tmp_path))

        mounts = aio_mod.AioSandboxProvider._get_thread_mounts(THREAD_ID, user_id=USER_A)

        host_paths = [m[0] for m in mounts]
        for host_path in host_paths:
            assert USER_A in _as_posix(host_path), f"Expected user_id in path: {host_path}"

    def test_get_thread_mounts_user_a_and_user_b_produce_distinct_sources(self, tmp_path, monkeypatch):
        aio_mod = importlib.import_module("deerflow.community.aio_sandbox.aio_sandbox_provider")
        monkeypatch.setattr(aio_mod, "get_paths", lambda: Paths(base_dir=tmp_path))

        mounts_a = aio_mod.AioSandboxProvider._get_thread_mounts(THREAD_ID, user_id=USER_A)
        mounts_b = aio_mod.AioSandboxProvider._get_thread_mounts(THREAD_ID, user_id=USER_B)

        # Container paths (index 1) are the same; host paths (index 0) must differ
        for (host_a, container_a, _), (host_b, container_b, _) in zip(mounts_a, mounts_b):
            assert container_a == container_b, "Container paths should be identical"
            assert host_a != host_b, f"Host paths should differ: {host_a} vs {host_b}"
            assert USER_A in _as_posix(host_a)
            assert USER_B in _as_posix(host_b)

    def test_get_thread_mounts_includes_acp_workspace_user_prefixed(self, tmp_path, monkeypatch):
        aio_mod = importlib.import_module("deerflow.community.aio_sandbox.aio_sandbox_provider")
        monkeypatch.setattr(aio_mod, "get_paths", lambda: Paths(base_dir=tmp_path))

        mounts = aio_mod.AioSandboxProvider._get_thread_mounts(THREAD_ID, user_id=USER_A)

        acp_mounts = [(h, c, ro) for h, c, ro in mounts if c == "/mnt/acp-workspace"]
        assert len(acp_mounts) == 1
        host_path, _, read_only = acp_mounts[0]
        assert USER_A in _as_posix(host_path)
        assert read_only is True


# ---------------------------------------------------------------------------
# Sandbox provider: acquire uses user-prefixed cache key
# ---------------------------------------------------------------------------


class TestSandboxProviderAcquireUserPrefixedKey:
    """acquire() uses user-prefixed cache key so same thread_id under two users gets distinct sandboxes."""

    def _make_provider(self):
        aio_mod = importlib.import_module("deerflow.community.aio_sandbox.aio_sandbox_provider")
        with patch.object(aio_mod.AioSandboxProvider, "_start_idle_checker"):
            provider = aio_mod.AioSandboxProvider.__new__(aio_mod.AioSandboxProvider)
            provider._config = {}
            provider._sandboxes = {}
            provider._sandbox_infos = {}
            provider._thread_sandboxes = {}
            provider._thread_locks = {}
            provider._lock = __import__("threading").Lock()
            provider._last_activity = {}
            provider._warm_pool = {}
            provider._idle_checker_stop = MagicMock()
        return provider

    def test_acquire_uses_user_prefixed_cache_key(self, tmp_path, monkeypatch):
        """Two users with the same thread_id get distinct sandbox IDs."""
        provider = self._make_provider()

        # Patch _create_sandbox to return a fake sandbox_id without actually creating containers
        created_sandboxes = []

        def _fake_create(thread_id, user_id, sandbox_id):
            created_sandboxes.append((thread_id, user_id, sandbox_id))
            # Register in provider state
            provider._sandboxes[sandbox_id] = MagicMock()
            provider._sandbox_infos[sandbox_id] = MagicMock()
            provider._last_activity[sandbox_id] = 0.0
            cache_key = f"{user_id}:{thread_id}" if (thread_id and user_id) else thread_id
            if cache_key:
                provider._thread_sandboxes[cache_key] = sandbox_id
            return sandbox_id

        with (
            patch.object(provider, "_create_sandbox", side_effect=_fake_create),
            patch.object(provider, "_discover_or_create_with_lock", side_effect=lambda tid, uid, ck, sid: _fake_create(tid, uid, sid)),
        ):
            id_a = provider.acquire(thread_id=THREAD_ID, user_id=USER_A)
            id_b = provider.acquire(thread_id=THREAD_ID, user_id=USER_B)

        assert id_a != id_b, "Same thread_id under two users must produce distinct sandbox IDs"

    def test_acquire_same_user_same_thread_reuses_sandbox(self, tmp_path, monkeypatch):
        """Same user + same thread_id reuses the existing sandbox."""
        provider = self._make_provider()

        def _fake_create(thread_id, user_id, sandbox_id):
            provider._sandboxes[sandbox_id] = MagicMock()
            provider._sandbox_infos[sandbox_id] = MagicMock()
            provider._last_activity[sandbox_id] = 0.0
            cache_key = f"{user_id}:{thread_id}" if (thread_id and user_id) else thread_id
            if cache_key:
                provider._thread_sandboxes[cache_key] = sandbox_id
            return sandbox_id

        with (
            patch.object(provider, "_create_sandbox", side_effect=_fake_create),
            patch.object(provider, "_discover_or_create_with_lock", side_effect=lambda tid, uid, ck, sid: _fake_create(tid, uid, sid)),
        ):
            id_first = provider.acquire(thread_id=THREAD_ID, user_id=USER_A)
            id_second = provider.acquire(thread_id=THREAD_ID, user_id=USER_A)

        assert id_first == id_second, "Same user + same thread_id should reuse the sandbox"
