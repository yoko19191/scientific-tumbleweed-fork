"""Tests for structured sandbox capacity errors in run worker events."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from deerflow.runtime.runs.schemas import RunStatus
from deerflow.runtime.runs.worker import run_agent
from deerflow.sandbox.exceptions import SandboxCapacityExceededError


def test_run_worker_publishes_structured_sandbox_capacity_error():
    async def cleanup(_run_id, delay=0):
        return None

    bridge = SimpleNamespace(publish=AsyncMock(), publish_end=AsyncMock(), cleanup=cleanup)
    run_manager = SimpleNamespace(set_status=AsyncMock())
    record = SimpleNamespace(run_id="run-1", thread_id="thread-1", abort_action=None)
    capacity = {
        "enabled": True,
        "backend": "local",
        "limit": 1,
        "active": 1,
        "warm": 0,
        "total": 1,
        "available": 0,
        "saturated": True,
    }

    def agent_factory(config):
        raise SandboxCapacityExceededError(capacity=capacity)

    asyncio.run(
        run_agent(
            bridge,
            run_manager,
            record,
            checkpointer=None,
            agent_factory=agent_factory,
            graph_input={},
            config={},
        )
    )

    run_manager.set_status.assert_any_await(
        "run-1",
        RunStatus.error,
        error="服务器沙盒容量已满，暂时无法创建新的沙盒，请稍后再试。",
    )
    error_events = [
        call.args[2]
        for call in bridge.publish.await_args_list
        if call.args[1] == "error"
    ]
    assert error_events[-1]["code"] == "SANDBOX_CAPACITY_EXCEEDED"
    assert error_events[-1]["capacity"] == capacity
