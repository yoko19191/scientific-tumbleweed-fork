"""Persistent MCP session pool for stateful stdio tool calls.

MCP ``ClientSession`` objects are backed by anyio task groups, so the task that
enters the session context must also exit it. The pool therefore gives every
session an owner task: callers receive the initialized session, while shutdown
paths only signal the owner task to close itself.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from collections import OrderedDict
from typing import Any

from mcp import ClientSession

logger = logging.getLogger(__name__)


class MCPSessionPool:
    """Manages persistent MCP sessions scoped by ``(server_name, scope_key)``."""

    MAX_SESSIONS = 256
    SESSION_CLOSE_TIMEOUT = 5.0

    def __init__(self) -> None:
        self._entries: OrderedDict[
            tuple[str, str],
            tuple[ClientSession, asyncio.AbstractEventLoop, asyncio.Task[Any], asyncio.Event],
        ] = OrderedDict()
        self._inflight: dict[
            tuple[str, str],
            tuple[asyncio.AbstractEventLoop, asyncio.Future[ClientSession], asyncio.Task[Any], asyncio.Event],
        ] = {}
        self._lock = threading.Lock()

    async def _run_session(
        self,
        connection: dict[str, Any],
        ready: asyncio.Future[ClientSession],
        close_evt: asyncio.Event,
    ) -> None:
        """Enter, initialize, and later exit one MCP session in the same task."""
        from langchain_mcp_adapters.sessions import create_session

        cm = create_session(connection)
        try:
            session = await cm.__aenter__()
        except BaseException as exc:
            if not ready.done():
                ready.set_exception(exc)
            return

        try:
            await session.initialize()
            if not ready.done():
                ready.set_result(session)
            await close_evt.wait()
        except BaseException as exc:
            if not ready.done():
                ready.set_exception(exc)
        finally:
            try:
                await cm.__aexit__(None, None, None)
            except Exception:
                logger.warning("Error closing MCP session", exc_info=True)

    async def get_session(self, server_name: str, scope_key: str, connection: dict[str, Any]) -> ClientSession:
        """Get or create a persistent MCP session."""
        key = (server_name, scope_key)
        current_loop = asyncio.get_running_loop()
        evicted: list[tuple[asyncio.AbstractEventLoop, asyncio.Task[Any], asyncio.Event, bool]] = []
        join: asyncio.Future[ClientSession] | None = None
        ready: asyncio.Future[ClientSession] | None = None
        close_evt: asyncio.Event | None = None
        task: asyncio.Task[Any] | None = None

        with self._lock:
            if key in self._entries:
                session, loop, owner_task, owner_close = self._entries[key]
                if loop is current_loop and not loop.is_closed():
                    self._entries.move_to_end(key)
                    return session
                self._entries.pop(key)
                evicted.append((loop, owner_task, owner_close, False))

            inflight = self._inflight.get(key)
            if inflight is not None and inflight[0] is current_loop and not inflight[0].is_closed():
                join = inflight[1]
            else:
                if inflight is not None:
                    self._inflight.pop(key)
                    evicted.append((inflight[0], inflight[2], inflight[3], True))

                ready = current_loop.create_future()
                close_evt = asyncio.Event()
                task = current_loop.create_task(self._run_session(connection, ready, close_evt))
                self._inflight[key] = (current_loop, ready, task, close_evt)

            while len(self._entries) >= self.MAX_SESSIONS:
                _oldest_key, (_session, loop, owner_task, owner_close) = next(iter(self._entries.items()))
                self._entries.pop(_oldest_key)
                evicted.append((loop, owner_task, owner_close, False))

        for loop, owner_task, owner_close, cancel in evicted:
            if loop is current_loop and not loop.is_closed():
                await self._shutdown(owner_close, owner_task, cancel)
            elif cancel:
                await self._shutdown_entry(loop, owner_task, owner_close, cancel=True)
            else:
                self._signal_close(loop, owner_close)

        if join is not None:
            return await asyncio.shield(join)

        assert ready is not None and close_evt is not None and task is not None
        try:
            session = await asyncio.shield(ready)
        except BaseException:
            owner_failed = ready.done() and not ready.cancelled() and ready.exception() is not None
            if not owner_failed:
                close_evt.set()
                task.cancel()
            try:
                await asyncio.shield(task)
            except BaseException:
                logger.debug("Owner task ended during get_session unwind", exc_info=True)
            with self._lock:
                if self._inflight.get(key) == (current_loop, ready, task, close_evt):
                    self._inflight.pop(key)
            raise

        with self._lock:
            still_ours = self._inflight.get(key) == (current_loop, ready, task, close_evt)
            if still_ours:
                self._inflight.pop(key)
                self._entries[key] = (session, current_loop, task, close_evt)
        if not still_ours:
            await self._shutdown(close_evt, task)
            raise asyncio.CancelledError("MCP session pool was closed while the session was being created")

        logger.info("Created persistent MCP session for %s/%s", server_name, scope_key)
        return session

    @staticmethod
    def _signal_close(loop: asyncio.AbstractEventLoop, close_evt: asyncio.Event) -> None:
        if loop.is_closed():
            return
        try:
            loop.call_soon_threadsafe(close_evt.set)
        except RuntimeError:
            pass

    async def _shutdown(self, close_evt: asyncio.Event, task: asyncio.Task[Any], cancel: bool = False) -> None:
        close_evt.set()
        if cancel:
            task.cancel()
        try:
            await task
        except (Exception, asyncio.CancelledError):
            logger.debug("Owner task ended during shutdown", exc_info=True)

    async def _shutdown_entry(
        self,
        loop: asyncio.AbstractEventLoop,
        task: asyncio.Task[Any],
        close_evt: asyncio.Event,
        cancel: bool = False,
    ) -> None:
        if loop.is_closed():
            return
        current_loop = asyncio.get_running_loop()
        if loop is current_loop:
            await self._shutdown(close_evt, task, cancel)
        elif loop.is_running():
            future = asyncio.run_coroutine_threadsafe(self._shutdown(close_evt, task, cancel), loop)
            try:
                await asyncio.wrap_future(future)
            except Exception:
                logger.warning("Error closing MCP session on owning loop", exc_info=True)
        else:
            logger.warning("Owning loop for MCP session is idle; signalling close best-effort")
            self._signal_close(loop, close_evt)
            if cancel:
                try:
                    loop.call_soon_threadsafe(task.cancel)
                except RuntimeError:
                    pass

    async def close_scope(self, scope_key: str) -> None:
        """Close all sessions for a given scope."""
        with self._lock:
            keys = [key for key in self._entries if key[1] == scope_key]
            entries = [self._entries.pop(key) for key in keys]
            inflight_keys = [key for key in self._inflight if key[1] == scope_key]
            inflight = [self._inflight.pop(key) for key in inflight_keys]

        for _session, loop, task, close_evt in entries:
            await self._shutdown_entry(loop, task, close_evt)
        for loop, _ready, task, close_evt in inflight:
            await self._shutdown_entry(loop, task, close_evt, cancel=True)

    async def close_server(self, server_name: str) -> None:
        """Close all sessions for a given server."""
        with self._lock:
            keys = [key for key in self._entries if key[0] == server_name]
            entries = [self._entries.pop(key) for key in keys]
            inflight_keys = [key for key in self._inflight if key[0] == server_name]
            inflight = [self._inflight.pop(key) for key in inflight_keys]

        for _session, loop, task, close_evt in entries:
            await self._shutdown_entry(loop, task, close_evt)
        for loop, _ready, task, close_evt in inflight:
            await self._shutdown_entry(loop, task, close_evt, cancel=True)

    async def close_all(self) -> None:
        """Close every managed session."""
        with self._lock:
            entries = list(self._entries.values())
            self._entries.clear()
            inflight = list(self._inflight.values())
            self._inflight.clear()

        for _session, loop, task, close_evt in entries:
            await self._shutdown_entry(loop, task, close_evt)
        for loop, _ready, task, close_evt in inflight:
            await self._shutdown_entry(loop, task, close_evt, cancel=True)

    def close_all_sync(self) -> None:
        """Synchronously signal all owner tasks to close on their own loops."""
        with self._lock:
            entries = list(self._entries.values())
            self._entries.clear()
            inflight = list(self._inflight.values())
            self._inflight.clear()

        owners = [(loop, task, close_evt, False) for _session, loop, task, close_evt in entries]
        owners += [(loop, task, close_evt, True) for loop, _ready, task, close_evt in inflight]
        try:
            current_running_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_running_loop = None

        for loop, task, close_evt, cancel in owners:
            if loop.is_closed():
                continue
            try:
                if loop is current_running_loop:
                    close_evt.set()
                    if cancel:
                        task.cancel()
                elif loop.is_running():
                    future = asyncio.run_coroutine_threadsafe(self._shutdown(close_evt, task, cancel), loop)
                    future.result(timeout=self.SESSION_CLOSE_TIMEOUT)
                else:
                    loop.run_until_complete(self._shutdown(close_evt, task, cancel))
            except Exception:
                logger.debug("Error closing MCP session during sync close", exc_info=True)


_pool: MCPSessionPool | None = None
_pool_lock = threading.Lock()


def get_session_pool() -> MCPSessionPool:
    """Return the global session-pool singleton."""
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                _pool = MCPSessionPool()
    return _pool


def reset_session_pool() -> None:
    """Reset the singleton (for tests)."""
    global _pool
    _pool = None
