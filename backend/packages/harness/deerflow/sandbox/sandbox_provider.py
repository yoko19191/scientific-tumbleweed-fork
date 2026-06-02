import asyncio
import threading
from abc import ABC, abstractmethod

from deerflow.config import get_app_config
from deerflow.reflection import resolve_class
from deerflow.sandbox.sandbox import Sandbox


class SandboxProvider(ABC):
    """Abstract base class for sandbox providers"""

    uses_thread_data_mounts: bool = False

    @abstractmethod
    def acquire(self, thread_id: str | None = None, user_id: str | None = None) -> str:
        """Acquire a sandbox environment and return its ID.

        Args:
            thread_id: Optional thread ID for thread-scoped sandboxes.
            user_id: Optional user ID for user-scoped path isolation.

        Returns:
            The ID of the acquired sandbox environment.
        """
        pass

    async def acquire_async(self, thread_id: str | None = None, user_id: str | None = None) -> str:
        """Acquire a sandbox without blocking the event loop.

        Most sandbox providers expose a synchronous lifecycle API because local
        Docker/provisioner operations are blocking. Async runtimes should call
        this method so those blocking operations run in a worker thread instead
        of stalling the event loop.
        """
        if user_id is None:
            return await asyncio.to_thread(self.acquire, thread_id)
        return await asyncio.to_thread(self.acquire, thread_id, user_id)

    @abstractmethod
    def get(self, sandbox_id: str) -> Sandbox | None:
        """Get a sandbox environment by ID.

        Args:
            sandbox_id: The ID of the sandbox environment to retain.
        """
        pass

    @abstractmethod
    def release(self, sandbox_id: str) -> None:
        """Release a sandbox environment.

        Args:
            sandbox_id: The ID of the sandbox environment to destroy.
        """
        pass

    def reset(self) -> None:
        """Clear cached state that survives provider instance replacement."""
        pass


_LOCAL_SANDBOX_PROVIDER_USE = "deerflow.sandbox.local:LocalSandboxProvider"
_default_sandbox_provider: SandboxProvider | None = None
_sandbox_providers_by_key: dict[str, SandboxProvider] = {}
_sandbox_provider_lock = threading.Lock()


def _resolve_provider_use(variant: str | None = None) -> str:
    if variant in {"chat", "local"}:
        return _LOCAL_SANDBOX_PROVIDER_USE
    config = get_app_config()
    return config.sandbox.use


def get_sandbox_provider(*, variant: str | None = None, provider_use: str | None = None, **kwargs) -> SandboxProvider:
    """Get a sandbox provider singleton.

    The default provider remains process-wide for compatibility. Passing
    ``variant="chat"`` returns a separate LocalSandboxProvider instance so chat
    and computer graphs can coexist in the same process.

    Returns:
        A sandbox provider instance.
    """
    global _default_sandbox_provider
    use = provider_use or _resolve_provider_use(variant)

    if provider_use is None and variant in {None, "computer", "default"}:
        with _sandbox_provider_lock:
            if _default_sandbox_provider is None:
                cls = resolve_class(use, SandboxProvider)
                _default_sandbox_provider = cls(**kwargs)
                _sandbox_providers_by_key[use] = _default_sandbox_provider
            return _default_sandbox_provider

    key = use
    with _sandbox_provider_lock:
        provider = _sandbox_providers_by_key.get(key)
        if provider is None:
            cls = resolve_class(use, SandboxProvider)
            provider = cls(**kwargs)
            _sandbox_providers_by_key[key] = provider
        return provider


def reset_sandbox_provider() -> None:
    """Reset the sandbox provider singleton.

    This clears the cached instance without calling shutdown.
    The next call to `get_sandbox_provider()` will create a new instance.
    Useful for testing or when switching configurations.

    Providers can override `reset()` to clear any module-level state they keep
    alive across instances (for example, `LocalSandboxProvider`'s cached
    `LocalSandbox` singleton). Without it, config/mount changes would not take
    effect on the next acquire().

    Note: If the provider has active sandboxes, they will be orphaned.
    Use `shutdown_sandbox_provider()` for proper cleanup.
    """
    global _default_sandbox_provider
    with _sandbox_provider_lock:
        providers = set(_sandbox_providers_by_key.values())
        if _default_sandbox_provider is not None:
            providers.add(_default_sandbox_provider)
        for provider in providers:
            provider.reset()
        _sandbox_providers_by_key.clear()
        _default_sandbox_provider = None


def shutdown_sandbox_provider() -> None:
    """Shutdown and reset the sandbox provider.

    This properly shuts down the provider (releasing all sandboxes)
    before clearing the singleton. Call this when the application
    is shutting down or when you need to completely reset the sandbox system.
    """
    global _default_sandbox_provider
    with _sandbox_provider_lock:
        providers = set(_sandbox_providers_by_key.values())
        if _default_sandbox_provider is not None:
            providers.add(_default_sandbox_provider)
        for provider in providers:
            if hasattr(provider, "shutdown"):
                provider.shutdown()
        _sandbox_providers_by_key.clear()
        _default_sandbox_provider = None


def set_sandbox_provider(provider: SandboxProvider) -> None:
    """Set a custom sandbox provider instance.

    This allows injecting a custom or mock provider for testing purposes.

    Args:
        provider: The SandboxProvider instance to use.
    """
    global _default_sandbox_provider
    with _sandbox_provider_lock:
        _default_sandbox_provider = provider
