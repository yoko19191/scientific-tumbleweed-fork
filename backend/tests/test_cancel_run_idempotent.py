"""Tests for idempotent run cancellation (issue #3055).

RunManager.cancel() returns True when a run is already interrupted so that
a second cancel request from the same worker is treated as a no-op success.
"""

from __future__ import annotations

import asyncio

from deerflow.runtime import RunManager, RunStatus

THREAD_ID = "thread-cancel-test"


# ---------------------------------------------------------------------------
# RunManager.cancel() unit tests
# ---------------------------------------------------------------------------


class TestRunManagerCancelIdempotency:
    def test_cancel_returns_true_for_already_interrupted_run(self):
        """cancel() must return True when the run is already interrupted."""

        async def run():
            mgr = RunManager()
            record = await mgr.create(THREAD_ID)
            await mgr.set_status(record.run_id, RunStatus.running)
            first = await mgr.cancel(record.run_id)
            assert first is True
            second = await mgr.cancel(record.run_id)
            assert second is True  # idempotent

        asyncio.run(run())

    def test_cancel_returns_false_for_successful_run(self):
        """cancel() must still return False for runs that completed successfully."""

        async def run():
            mgr = RunManager()
            record = await mgr.create(THREAD_ID)
            await mgr.set_status(record.run_id, RunStatus.running)
            await mgr.set_status(record.run_id, RunStatus.success)
            result = await mgr.cancel(record.run_id)
            assert result is False

        asyncio.run(run())

    def test_cancel_returns_false_for_unknown_run(self):
        async def run():
            mgr = RunManager()
            result = await mgr.cancel("nonexistent-run-id")
            assert result is False

        asyncio.run(run())
