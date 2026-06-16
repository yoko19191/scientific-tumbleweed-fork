"""End-to-end deferred promotion loop with a deterministic fake model."""

from __future__ import annotations

import asyncio

from langchain.agents import create_agent
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool as as_tool

from deerflow.agents.middlewares.deferred_tool_filter_middleware import DeferredToolFilterMiddleware
from deerflow.agents.thread_state import ThreadState
from deerflow.tools.builtins.tool_search import assemble_deferred_tools
from deerflow.tools.mcp_metadata import tag_mcp_tool


@as_tool
def active_tool(x: str) -> str:
    """An always-active local tool."""
    return x


@as_tool
def mcp_calc(expression: str) -> str:
    """Evaluate arithmetic."""
    return expression


@as_tool
def mcp_other(x: str) -> str:
    """Another deferred MCP tool."""
    return x


def test_tool_search_promotes_into_next_turn():
    bound: list[list[str | None]] = []

    class RecordingModel(GenericFakeChatModel):
        def bind_tools(self, tools, **kwargs):
            bound.append([getattr(tool, "name", None) for tool in tools])
            return self

    final_tools, setup = assemble_deferred_tools([active_tool, tag_mcp_tool(mcp_calc), tag_mcp_tool(mcp_other)], enabled=True)
    turn1 = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "tool_search",
                "args": {"query": "select:mcp_calc"},
                "id": "call-1",
                "type": "tool_call",
            }
        ],
    )
    turn2 = AIMessage(content="done")
    model = RecordingModel(messages=iter([turn1, turn2]))

    graph = create_agent(
        model=model,
        tools=final_tools,
        middleware=[DeferredToolFilterMiddleware(setup.deferred_names, setup.catalog_hash)],
        state_schema=ThreadState,
    )

    result = asyncio.run(graph.ainvoke({"messages": [HumanMessage(content="use the deferred calculator")]}))

    assert len(bound) >= 2
    assert "mcp_calc" not in bound[0]
    assert "mcp_other" not in bound[0]
    assert "mcp_calc" in bound[1]
    assert "mcp_other" not in bound[1]
    assert result["promoted"] == {"catalog_hash": setup.catalog_hash, "names": ["mcp_calc"]}
