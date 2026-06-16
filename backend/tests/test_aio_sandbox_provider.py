"""Tests for AioSandboxProvider mount helpers."""

import importlib
import threading
import weakref
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from deerflow.config.paths import Paths, join_host_path
from deerflow.sandbox.exceptions import SandboxCapacityExceededError

# ── ensure_thread_dirs ───────────────────────────────────────────────────────


def test_ensure_thread_dirs_creates_acp_workspace(tmp_path):
    """ACP workspace directory must be created alongside user-data dirs."""
    paths = Paths(base_dir=tmp_path)
    paths.ensure_thread_dirs("thread-1")

    assert (tmp_path / "threads" / "thread-1" / "user-data" / "workspace").exists()
    assert (tmp_path / "threads" / "thread-1" / "user-data" / "uploads").exists()
    assert (tmp_path / "threads" / "thread-1" / "user-data" / "outputs").exists()
    assert (tmp_path / "threads" / "thread-1" / "acp-workspace").exists()


def test_ensure_thread_dirs_acp_workspace_is_world_writable(tmp_path):
    """ACP workspace must be chmod 0o777 so the ACP subprocess can write into it."""
    paths = Paths(base_dir=tmp_path)
    paths.ensure_thread_dirs("thread-2")

    acp_dir = tmp_path / "threads" / "thread-2" / "acp-workspace"
    mode = oct(acp_dir.stat().st_mode & 0o777)
    assert mode == oct(0o777)


def test_host_thread_dir_rejects_invalid_thread_id(tmp_path):
    paths = Paths(base_dir=tmp_path)

    with pytest.raises(ValueError, match="Invalid thread_id"):
        paths.host_thread_dir("../escape")


# ── _get_thread_mounts ───────────────────────────────────────────────────────


def _make_provider(tmp_path):
    """Build a minimal AioSandboxProvider instance without starting the idle checker."""
    aio_mod = importlib.import_module("deerflow.community.aio_sandbox.aio_sandbox_provider")
    with patch.object(aio_mod.AioSandboxProvider, "_start_idle_checker"):
        provider = aio_mod.AioSandboxProvider.__new__(aio_mod.AioSandboxProvider)
        provider._config = {}
        provider._sandboxes = {}
        provider._lock = MagicMock()
        provider._idle_checker_stop = MagicMock()
    return provider


def _make_provider_with_active_sandbox(tmp_path, sandbox_id: str):
    aio_mod = importlib.import_module("deerflow.community.aio_sandbox.aio_sandbox_provider")
    provider = aio_mod.AioSandboxProvider.__new__(aio_mod.AioSandboxProvider)
    sandbox = MagicMock()
    sandbox.id = sandbox_id
    info = aio_mod.SandboxInfo(sandbox_id=sandbox_id, sandbox_url=f"http://{sandbox_id}")
    provider._config = {"replicas": 3}
    provider._backend = SimpleNamespace(
        is_alive=MagicMock(return_value=True),
        destroy=MagicMock(),
        discover=MagicMock(return_value=None),
        create=MagicMock(),
    )
    provider._lock = threading.Lock()
    provider._thread_locks = weakref.WeakValueDictionary()
    provider._sandboxes = {sandbox_id: sandbox}
    provider._sandbox_infos = {sandbox_id: info}
    provider._thread_sandboxes = {}
    provider._last_activity = {sandbox_id: 1.0}
    provider._warm_pool = {}
    return provider, sandbox, info


def test_get_thread_mounts_includes_acp_workspace(tmp_path, monkeypatch):
    """_get_thread_mounts must include /mnt/acp-workspace (read-only) for docker sandbox."""
    aio_mod = importlib.import_module("deerflow.community.aio_sandbox.aio_sandbox_provider")
    monkeypatch.setattr(aio_mod, "get_paths", lambda: Paths(base_dir=tmp_path))

    mounts = aio_mod.AioSandboxProvider._get_thread_mounts("thread-3")

    container_paths = {m[1]: (m[0], m[2]) for m in mounts}

    assert "/mnt/acp-workspace" in container_paths, "ACP workspace mount is missing"
    expected_host = str(tmp_path / "threads" / "thread-3" / "acp-workspace")
    actual_host, read_only = container_paths["/mnt/acp-workspace"]
    assert actual_host == expected_host
    assert read_only is True, "ACP workspace should be read-only inside the sandbox"


def test_get_thread_mounts_includes_user_data_dirs(tmp_path, monkeypatch):
    """Baseline: user-data mounts must still be present after the ACP workspace change."""
    aio_mod = importlib.import_module("deerflow.community.aio_sandbox.aio_sandbox_provider")
    monkeypatch.setattr(aio_mod, "get_paths", lambda: Paths(base_dir=tmp_path))

    mounts = aio_mod.AioSandboxProvider._get_thread_mounts("thread-4")
    container_paths = {m[1] for m in mounts}

    assert "/mnt/user-data/workspace" in container_paths
    assert "/mnt/user-data/uploads" in container_paths
    assert "/mnt/user-data/outputs" in container_paths


def test_join_host_path_preserves_windows_drive_letter_style():
    base = r"C:\Users\demo\deer-flow\backend\.deer-flow"

    joined = join_host_path(base, "threads", "thread-9", "user-data", "outputs")

    assert joined == r"C:\Users\demo\deer-flow\backend\.deer-flow\threads\thread-9\user-data\outputs"


def test_get_thread_mounts_preserves_windows_host_path_style(tmp_path, monkeypatch):
    """Docker bind mount sources must keep Windows-style paths intact."""
    aio_mod = importlib.import_module("deerflow.community.aio_sandbox.aio_sandbox_provider")
    monkeypatch.setenv("DEER_FLOW_HOST_BASE_DIR", r"C:\Users\demo\deer-flow\backend\.deer-flow")
    monkeypatch.setattr(aio_mod, "get_paths", lambda: Paths(base_dir=tmp_path))

    mounts = aio_mod.AioSandboxProvider._get_thread_mounts("thread-10")

    container_paths = {container_path: host_path for host_path, container_path, _ in mounts}

    assert container_paths["/mnt/user-data/workspace"] == r"C:\Users\demo\deer-flow\backend\.deer-flow\threads\thread-10\user-data\workspace"
    assert container_paths["/mnt/user-data/uploads"] == r"C:\Users\demo\deer-flow\backend\.deer-flow\threads\thread-10\user-data\uploads"
    assert container_paths["/mnt/user-data/outputs"] == r"C:\Users\demo\deer-flow\backend\.deer-flow\threads\thread-10\user-data\outputs"
    assert container_paths["/mnt/acp-workspace"] == r"C:\Users\demo\deer-flow\backend\.deer-flow\threads\thread-10\acp-workspace"


def test_discover_or_create_only_unlocks_when_lock_succeeds(tmp_path, monkeypatch):
    """Unlock should not run if exclusive locking itself fails."""
    aio_mod = importlib.import_module("deerflow.community.aio_sandbox.aio_sandbox_provider")
    provider = _make_provider(tmp_path)
    provider._discover_or_create_with_lock = aio_mod.AioSandboxProvider._discover_or_create_with_lock.__get__(
        provider,
        aio_mod.AioSandboxProvider,
    )

    monkeypatch.setattr(aio_mod, "get_paths", lambda: Paths(base_dir=tmp_path))
    monkeypatch.setattr(
        aio_mod,
        "_lock_file_exclusive",
        lambda _lock_file: (_ for _ in ()).throw(RuntimeError("lock failed")),
    )

    unlock_calls: list[object] = []
    monkeypatch.setattr(
        aio_mod,
        "_unlock_file",
        lambda lock_file: unlock_calls.append(lock_file),
    )

    with patch.object(provider, "_create_sandbox", return_value="sandbox-id"):
        with pytest.raises(RuntimeError, match="lock failed"):
            provider._discover_or_create_with_lock("thread-5", None, "thread-5", "sandbox-5")

    assert unlock_calls == []


def test_load_config_uses_scientific_tumbleweed_sandbox_prefix_by_default(monkeypatch):
    """Default sandbox containers should use the scientific-tumbleweed prefix."""
    aio_mod = importlib.import_module("deerflow.community.aio_sandbox.aio_sandbox_provider")
    provider = aio_mod.AioSandboxProvider.__new__(aio_mod.AioSandboxProvider)

    monkeypatch.setattr(
        aio_mod,
        "get_app_config",
        lambda: SimpleNamespace(
            sandbox=SimpleNamespace(
                image=None,
                port=None,
                container_prefix=None,
                idle_timeout=None,
                replicas=None,
                mounts=[],
                environment={},
                provisioner_url=None,
            )
        ),
    )

    config = aio_mod.AioSandboxProvider._load_config(provider)

    assert config["container_prefix"] == "scientific-tumbleweed-sandbox"


def test_load_config_preserves_sandbox_resources(monkeypatch):
    """Resource requests/limits should flow from config.yaml into AIO config."""
    aio_mod = importlib.import_module("deerflow.community.aio_sandbox.aio_sandbox_provider")
    provider = aio_mod.AioSandboxProvider.__new__(aio_mod.AioSandboxProvider)

    resources = {
        "requests": {"cpu": "100m", "memory": "256Mi", "ephemeral-storage": "500Mi"},
        "limits": {"cpu": "2", "memory": "4Gi", "ephemeral-storage": "10Gi"},
    }
    monkeypatch.setattr(
        aio_mod,
        "get_app_config",
        lambda: SimpleNamespace(
            sandbox=SimpleNamespace(
                image=None,
                port=None,
                container_prefix=None,
                idle_timeout=None,
                replicas=None,
                mounts=[],
                environment={},
                resources=resources,
                provisioner_url=None,
            )
        ),
    )

    config = aio_mod.AioSandboxProvider._load_config(provider)

    assert config["resources"] == resources


def test_get_capacity_counts_active_and_warm_sandboxes(tmp_path):
    """Capacity should count both active and warm sandboxes."""
    aio_mod = importlib.import_module("deerflow.community.aio_sandbox.aio_sandbox_provider")
    provider = aio_mod.AioSandboxProvider.__new__(aio_mod.AioSandboxProvider)
    provider._config = {"replicas": 3}
    provider._backend = MagicMock()
    provider._lock = threading.Lock()
    provider._sandboxes = {"active-1": object(), "active-2": object()}
    provider._warm_pool = {"warm-1": (MagicMock(), 123.0)}

    capacity = aio_mod.AioSandboxProvider.get_capacity(provider)

    assert capacity == {
        "enabled": True,
        "backend": "local",
        "limit": 3,
        "active": 2,
        "warm": 1,
        "total": 3,
        "available": 0,
        "saturated": True,
    }


def test_create_sandbox_raises_capacity_error_when_active_slots_are_full(monkeypatch):
    """Replicas should be a hard cap when no warm sandbox can be evicted."""
    aio_mod = importlib.import_module("deerflow.community.aio_sandbox.aio_sandbox_provider")
    provider = aio_mod.AioSandboxProvider.__new__(aio_mod.AioSandboxProvider)
    provider._config = {"replicas": 1}
    provider._backend = MagicMock()
    provider._lock = threading.Lock()
    provider._sandboxes = {"active-1": object()}
    provider._warm_pool = {}
    provider._get_extra_mounts = lambda _thread_id, _user_id: []

    with pytest.raises(SandboxCapacityExceededError) as exc_info:
        aio_mod.AioSandboxProvider._create_sandbox(provider, "thread-1", None, "sandbox-2")

    assert exc_info.value.code == "SANDBOX_CAPACITY_EXCEEDED"
    assert exc_info.value.capacity["limit"] == 1
    provider._backend.create.assert_not_called()


def test_create_sandbox_evicts_warm_pool_before_enforcing_capacity(monkeypatch):
    """Warm sandboxes should be reclaimed before rejecting new sandbox creation."""
    aio_mod = importlib.import_module("deerflow.community.aio_sandbox.aio_sandbox_provider")
    provider = aio_mod.AioSandboxProvider.__new__(aio_mod.AioSandboxProvider)
    provider._config = {"replicas": 1}
    provider._backend = MagicMock()
    provider._lock = threading.Lock()
    provider._sandboxes = {}
    provider._sandbox_infos = {}
    provider._last_activity = {}
    provider._thread_sandboxes = {}
    provider._warm_pool = {"warm-1": (MagicMock(sandbox_id="warm-1"), 123.0)}
    provider._get_extra_mounts = lambda _thread_id, _user_id: []

    info = MagicMock(sandbox_id="sandbox-2", sandbox_url="http://sandbox.example")
    provider._backend.create.return_value = info
    monkeypatch.setattr(aio_mod, "wait_for_sandbox_ready", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(aio_mod, "AioSandbox", lambda id, base_url: SimpleNamespace(id=id, base_url=base_url))

    sandbox_id = aio_mod.AioSandboxProvider._create_sandbox(provider, "thread-1", None, "sandbox-2")

    assert sandbox_id == "sandbox-2"
    provider._backend.destroy.assert_called_once()
    provider._backend.create.assert_called_once()


@pytest.mark.anyio
async def test_create_sandbox_async_uses_async_readiness_polling(monkeypatch):
    """Async sandbox creation should not block on synchronous readiness polling."""
    aio_mod = importlib.import_module("deerflow.community.aio_sandbox.aio_sandbox_provider")
    provider = aio_mod.AioSandboxProvider.__new__(aio_mod.AioSandboxProvider)
    provider._config = {"replicas": 3}
    provider._backend = SimpleNamespace(
        create=MagicMock(return_value=aio_mod.SandboxInfo(sandbox_id="sandbox-async", sandbox_url="http://sandbox")),
        destroy=MagicMock(),
    )
    provider._lock = threading.Lock()
    provider._sandboxes = {}
    provider._sandbox_infos = {}
    provider._thread_sandboxes = {}
    provider._last_activity = {}
    provider._warm_pool = {}
    provider._get_extra_mounts = lambda _thread_id, _user_id: []

    async_readiness_calls: list[tuple[str, int]] = []

    async def fake_wait_for_sandbox_ready_async(sandbox_url: str, timeout: int = 30, poll_interval: float = 1.0) -> bool:
        async_readiness_calls.append((sandbox_url, timeout))
        return True

    monkeypatch.setattr(aio_mod, "wait_for_sandbox_ready_async", fake_wait_for_sandbox_ready_async)
    monkeypatch.setattr(
        aio_mod,
        "wait_for_sandbox_ready",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("sync readiness should not be used")),
    )

    sandbox_id = await aio_mod.AioSandboxProvider._create_sandbox_async(
        provider,
        "thread-async",
        "user-async",
        "user-async:thread-async",
        "sandbox-async",
    )

    assert sandbox_id == "sandbox-async"
    assert async_readiness_calls == [("http://sandbox", 60)]
    assert provider._backend.destroy.call_count == 0
    assert provider._thread_sandboxes["user-async:thread-async"] == "sandbox-async"


@pytest.mark.anyio
async def test_acquire_async_uses_user_scoped_cache_key(monkeypatch):
    """Async acquisition should preserve the fork's user_id sandbox isolation."""
    aio_mod = importlib.import_module("deerflow.community.aio_sandbox.aio_sandbox_provider")
    provider = aio_mod.AioSandboxProvider.__new__(aio_mod.AioSandboxProvider)
    provider._lock = threading.Lock()
    provider._thread_locks = weakref.WeakValueDictionary()

    calls: list[tuple[str | None, str | None, str | None]] = []

    async def fake_acquire_internal_async(thread_id: str | None, user_id: str | None, cache_key: str | None) -> str:
        calls.append((thread_id, user_id, cache_key))
        return "sandbox-user"

    monkeypatch.setattr(provider, "_acquire_internal_async", fake_acquire_internal_async)

    assert await provider.acquire_async("thread-1", "user-1") == "sandbox-user"
    assert calls == [("thread-1", "user-1", "user-1:thread-1")]


@pytest.mark.anyio
async def test_acquire_internal_async_offloads_cached_reuse_health_check(tmp_path, monkeypatch):
    aio_mod = importlib.import_module("deerflow.community.aio_sandbox.aio_sandbox_provider")
    provider, _sandbox, _info = _make_provider_with_active_sandbox(tmp_path, "sandbox-cached-async")
    provider._thread_sandboxes = {"user-1:thread-1": "sandbox-cached-async"}

    to_thread_calls: list[tuple[object, tuple[object, ...]]] = []

    async def fake_to_thread(func, /, *args, **kwargs):
        to_thread_calls.append((func, args))
        return func(*args, **kwargs)

    monkeypatch.setattr(aio_mod.asyncio, "to_thread", fake_to_thread)

    sandbox_id = await provider._acquire_internal_async("thread-1", "user-1", "user-1:thread-1")

    assert sandbox_id == "sandbox-cached-async"
    assert to_thread_calls == [(provider._reuse_in_process_sandbox, ("user-1:thread-1", "thread-1"))]


def test_get_uses_in_memory_registry_only(tmp_path):
    provider, sandbox, _info = _make_provider_with_active_sandbox(tmp_path, "sandbox-live")
    provider._backend.is_alive = MagicMock(side_effect=AssertionError("get must not call backend health checks"))

    assert provider.get("sandbox-live") is sandbox


def test_reuse_in_process_drops_dead_cached_sandbox(tmp_path):
    provider, sandbox, info = _make_provider_with_active_sandbox(tmp_path, "sandbox-dead")
    provider._thread_sandboxes = {"thread-dead": "sandbox-dead"}
    provider._backend.is_alive = MagicMock(return_value=False)

    assert provider._reuse_in_process_sandbox("thread-dead", "thread-dead") is None

    sandbox.close.assert_called_once_with()
    provider._backend.destroy.assert_called_once_with(info)
    assert "sandbox-dead" not in provider._sandboxes
    assert "sandbox-dead" not in provider._sandbox_infos
    assert provider._thread_sandboxes == {}


def test_reuse_in_process_keeps_cached_sandbox_when_health_check_errors(tmp_path):
    provider, sandbox, _info = _make_provider_with_active_sandbox(tmp_path, "sandbox-transient")
    provider._thread_sandboxes = {"thread-transient": "sandbox-transient"}
    provider._backend.is_alive = MagicMock(side_effect=OSError("docker daemon busy"))

    assert provider._reuse_in_process_sandbox("thread-transient", "thread-transient") == "sandbox-transient"

    sandbox.close.assert_not_called()
    provider._backend.destroy.assert_not_called()
    assert provider._sandboxes["sandbox-transient"] is sandbox


def test_drop_unhealthy_sandbox_skips_recreated_entry(tmp_path):
    aio_mod = importlib.import_module("deerflow.community.aio_sandbox.aio_sandbox_provider")
    provider = aio_mod.AioSandboxProvider.__new__(aio_mod.AioSandboxProvider)
    old_info = aio_mod.SandboxInfo(sandbox_id="sandbox-toctou", sandbox_url="http://old-sandbox")
    new_info = aio_mod.SandboxInfo(sandbox_id="sandbox-toctou", sandbox_url="http://new-sandbox")
    new_sandbox = MagicMock()
    provider._lock = threading.Lock()
    provider._backend = SimpleNamespace(destroy=MagicMock())
    provider._sandboxes = {"sandbox-toctou": new_sandbox}
    provider._sandbox_infos = {"sandbox-toctou": new_info}
    provider._thread_sandboxes = {"thread-toctou": "sandbox-toctou"}
    provider._last_activity = {"sandbox-toctou": 1.0}
    provider._warm_pool = {}

    provider._drop_unhealthy_sandbox("sandbox-toctou", "stale health check", expected_info=old_info)

    new_sandbox.close.assert_not_called()
    provider._backend.destroy.assert_not_called()
    assert provider._sandbox_infos["sandbox-toctou"] is new_info
    assert provider._sandboxes["sandbox-toctou"] is new_sandbox
    assert provider._thread_sandboxes == {"thread-toctou": "sandbox-toctou"}


def test_reclaim_warm_pool_drops_dead_sandbox(tmp_path):
    aio_mod = importlib.import_module("deerflow.community.aio_sandbox.aio_sandbox_provider")
    provider = aio_mod.AioSandboxProvider.__new__(aio_mod.AioSandboxProvider)
    info = aio_mod.SandboxInfo(sandbox_id="sandbox-warm-dead", sandbox_url="http://stale-sandbox")
    provider._lock = threading.Lock()
    provider._backend = SimpleNamespace(is_alive=MagicMock(return_value=False), destroy=MagicMock())
    provider._sandboxes = {}
    provider._sandbox_infos = {}
    provider._thread_sandboxes = {}
    provider._last_activity = {}
    provider._warm_pool = {"sandbox-warm-dead": (info, 0.0)}

    assert provider._reclaim_warm_pool_sandbox("thread-warm", "thread-warm", "sandbox-warm-dead") is None

    provider._backend.destroy.assert_called_once_with(info)
    assert provider._warm_pool == {}


def test_remote_backend_posts_configured_image(monkeypatch):
    """Remote provisioner requests should carry the image from config.yaml."""
    remote_mod = importlib.import_module("deerflow.community.aio_sandbox.remote_backend")
    backend = remote_mod.RemoteSandboxBackend(
        provisioner_url="http://provisioner:8002",
        image="custom-sandbox:arm64",
    )

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"sandbox_url": "http://sandbox.example"}

    post_calls = []

    def fake_post(url, json, timeout):
        post_calls.append({"url": url, "json": json, "timeout": timeout})
        return FakeResponse()

    monkeypatch.setattr(remote_mod.requests, "post", fake_post)

    backend.create("thread-1", "sandbox-1")

    assert post_calls[0]["json"]["image"] == "custom-sandbox:arm64"


def test_remote_backend_posts_configured_resources(monkeypatch):
    """Remote provisioner requests should carry resource config from config.yaml."""
    remote_mod = importlib.import_module("deerflow.community.aio_sandbox.remote_backend")
    resources = {
        "requests": {"cpu": "100m", "memory": "256Mi", "ephemeral-storage": "500Mi"},
        "limits": {"cpu": "2", "memory": "4Gi", "ephemeral-storage": "10Gi"},
    }
    backend = remote_mod.RemoteSandboxBackend(
        provisioner_url="http://provisioner:8002",
        image="custom-sandbox:arm64",
        resources=resources,
    )

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"sandbox_url": "http://sandbox.example"}

    post_calls = []

    def fake_post(url, json, timeout):
        post_calls.append({"url": url, "json": json, "timeout": timeout})
        return FakeResponse()

    monkeypatch.setattr(remote_mod.requests, "post", fake_post)

    backend.create("thread-1", "sandbox-1")

    assert post_calls[0]["json"]["resources"] == resources


def test_remote_backend_create_forwards_user_id(monkeypatch):
    """Provisioner mode must receive user_id so PVC subPath matches user isolation."""
    remote_mod = importlib.import_module("deerflow.community.aio_sandbox.remote_backend")
    backend = remote_mod.RemoteSandboxBackend("http://provisioner:8002")
    posted: dict = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"sandbox_url": "http://sandbox.local"}

    def fake_post(url, json, timeout):  # noqa: A002 - mirrors requests.post kwarg
        posted.update({"url": url, "json": json, "timeout": timeout})
        return FakeResponse()

    monkeypatch.setattr(remote_mod.requests, "post", fake_post)

    backend.create("thread-42", "sandbox-42", user_id="user-7")

    assert posted["url"] == "http://provisioner:8002/api/sandboxes"
    assert posted["json"] == {
        "sandbox_id": "sandbox-42",
        "thread_id": "thread-42",
        "user_id": "user-7",
        "image": None,
    }
