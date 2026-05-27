"""Tests for token usage attribution middleware."""

from __future__ import annotations

import importlib

from langchain_core.messages import AIMessage, ToolMessage

from deerflow.agents.middlewares.token_usage_middleware import SUBAGENT_USAGE_KEY, TOKEN_USAGE_ATTRIBUTION_KEY, TokenUsageMiddleware


def test_token_usage_middleware_adds_tool_attribution():
    message = AIMessage(
        content="",
        tool_calls=[{"name": "web_search", "args": {"query": "paper"}, "id": "call-1"}],
        usage_metadata={"input_tokens": 10, "output_tokens": 2, "total_tokens": 12},
    )

    update = TokenUsageMiddleware()._apply({"messages": [message], "todos": []})

    assert update is not None
    updated = update["messages"][0]
    attribution = updated.additional_kwargs[TOKEN_USAGE_ATTRIBUTION_KEY]
    assert attribution["kind"] == "tool_batch"
    assert attribution["actions"] == [
        {
            "kind": "search",
            "tool_name": "web_search",
            "query": "paper",
            "tool_call_id": "call-1",
        }
    ]


def test_token_usage_middleware_writes_back_subagent_usage(monkeypatch):
    dispatch = AIMessage(
        content="",
        tool_calls=[{"name": "task", "args": {"description": "Analyze"}, "id": "task-1"}],
        usage_metadata={"input_tokens": 5, "output_tokens": 1, "total_tokens": 6},
    )
    tool = ToolMessage(content="done", tool_call_id="task-1")
    next_ai = AIMessage(content="Final", usage_metadata={"input_tokens": 7, "output_tokens": 3, "total_tokens": 10})

    task_tool_module = importlib.import_module("deerflow.tools.builtins.task_tool")
    monkeypatch.setattr(task_tool_module, "pop_cached_subagent_usage", lambda tool_call_id: {"input_tokens": 11, "output_tokens": 4, "total_tokens": 15} if tool_call_id == "task-1" else None)

    update = TokenUsageMiddleware()._apply({"messages": [dispatch, tool, next_ai], "todos": []})

    assert update is not None
    updated_dispatch = update["messages"][0]
    assert updated_dispatch.usage_metadata == {"input_tokens": 16, "output_tokens": 5, "total_tokens": 21}
    assert updated_dispatch.additional_kwargs[SUBAGENT_USAGE_KEY] == {
        "input_tokens": 11,
        "output_tokens": 4,
        "total_tokens": 15,
    }
