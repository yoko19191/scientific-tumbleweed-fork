"""Tests for thread run helpers used by run routers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from deerflow.runtime import read_thread_final_state, thread_checkpoint_config
from deerflow.runtime.runs.checkpoints import read_thread_checkpoint_values


def test_thread_checkpoint_config_uses_root_checkpoint_namespace():
    assert thread_checkpoint_config("thread-1") == {
        "configurable": {"thread_id": "thread-1", "checkpoint_ns": ""}
    }


@pytest.mark.anyio
async def test_read_thread_final_state_serializes_checkpoint_values():
    checkpointer = MagicMock()
    checkpointer.aget_tuple = AsyncMock(
        return_value=SimpleNamespace(
            checkpoint={
                "channel_values": {
                    "title": "Research",
                    "__interrupt__": {"hidden": True},
                    "__pregel_tasks": ["internal"],
                }
            }
        )
    )

    final_state = await read_thread_final_state(checkpointer, "thread-1")

    assert final_state == {"title": "Research"}
    checkpointer.aget_tuple.assert_awaited_once_with(
        {"configurable": {"thread_id": "thread-1", "checkpoint_ns": ""}}
    )


@pytest.mark.anyio
async def test_read_thread_checkpoint_values_returns_none_without_checkpoint():
    checkpointer = MagicMock()
    checkpointer.aget_tuple = AsyncMock(return_value=None)

    assert await read_thread_checkpoint_values(checkpointer, "thread-1") is None
