"""Tests for Langfuse metadata injection in run worker."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from deerflow.runtime.runs.manager import RunManager
from deerflow.runtime.runs.worker import run_agent
from deerflow.tracing import metadata as tracing_metadata


@pytest.mark.anyio
async def test_run_agent_injects_langfuse_metadata(monkeypatch):
    monkeypatch.setattr(tracing_metadata, "get_enabled_tracing_providers", lambda: ["langfuse"])
    run_manager = RunManager()
    record = await run_manager.create("thread-1", assistant_id="chat_lead_agent", metadata={"user_id": "user-1"})
    run_manager.cleanup = AsyncMock()  # type: ignore[method-assign]
    record.model_name = "deepseek-v3"
    bridge = SimpleNamespace(publish=AsyncMock(), publish_end=AsyncMock(), cleanup=AsyncMock())
    captured = {}

    class DummyAgent:
        metadata = {"model_name": "deepseek-v3"}

        async def astream(self, graph_input, config=None, stream_mode=None, subgraphs=False):
            captured["metadata"] = config["metadata"]
            yield {"messages": []}

    def factory(*, config):
        captured["factory_metadata"] = config["metadata"]
        return DummyAgent()

    await run_agent(
        bridge,
        run_manager,
        record,
        checkpointer=None,
        agent_factory=factory,
        graph_input={},
        config={"metadata": {"user_id": "user-1"}},
    )

    assert captured["factory_metadata"]["langfuse_session_id"] == "thread-1"
    assert captured["factory_metadata"]["langfuse_user_id"] == "user-1"
    assert captured["metadata"]["langfuse_trace_name"] == "chat_lead_agent"
    assert "model:deepseek-v3" in captured["metadata"]["langfuse_tags"]
