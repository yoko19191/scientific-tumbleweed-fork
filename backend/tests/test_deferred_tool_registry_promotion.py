"""Regression tests for graph-state deferred tool promotion.

The old implementation kept deferred tools in a ContextVar registry. Building
or re-entering tool setup in a sibling context could wipe promotions. The new
implementation keeps the deferred catalog in closures and promotion in graph
state.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from langchain.agents import create_agent
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool as as_tool

from deerflow.agents.middlewares.deferred_tool_filter_middleware import DeferredToolFilterMiddleware
from deerflow.skills.tool_policy import filter_tools_by_skill_allowed_tools
from deerflow.skills.types import Skill
from deerflow.tools.builtins.tool_search import DeferredToolSetup, assemble_deferred_tools, build_deferred_tool_setup
from deerflow.tools.mcp_metadata import tag_mcp_tool


@as_tool
def active_tool(x: str) -> str:
    """Active local tool."""
    return x


@as_tool
def mcp_secret(x: str) -> str:
    """Deferred MCP tool."""
    return x


_BOUND: list[list[str | None]] = []


class _RecordingModel(GenericFakeChatModel):
    def bind_tools(self, tools, **kwargs):
        _BOUND.append([getattr(tool, "name", None) for tool in tools])
        return self


def _build_graph():
    filtered = [active_tool, tag_mcp_tool(mcp_secret)]
    final_tools, setup = assemble_deferred_tools(filtered, enabled=True)
    model = _RecordingModel(messages=iter([AIMessage(content="done")] * 4))
    return create_agent(
        model=model,
        tools=final_tools,
        middleware=[DeferredToolFilterMiddleware(setup.deferred_names, setup.catalog_hash)],
        system_prompt="test",
    )


async def _abuild():
    return _build_graph()


def test_deferred_hidden_when_built_and_run_in_different_contexts():
    _BOUND.clear()

    async def main():
        graph = await asyncio.create_task(_abuild())

        async def run():
            await graph.ainvoke({"messages": [HumanMessage(content="hi")]})

        await asyncio.create_task(run())

    asyncio.run(main())

    assert _BOUND
    assert not any("mcp_secret" in names for names in _BOUND)


def test_policy_excluded_mcp_tool_not_in_catalog():
    setup = build_deferred_tool_setup([active_tool], enabled=True)
    assert setup.deferred_names == frozenset()
    assert setup.tool_search_tool is None


def test_fail_closed_when_mcp_survives_without_setup(monkeypatch):
    monkeypatch.setattr(
        "deerflow.tools.builtins.tool_search.build_deferred_tool_setup",
        lambda tools, *, enabled: DeferredToolSetup(None, frozenset(), None),
    )
    with pytest.raises(RuntimeError, match="fail-closed"):
        assemble_deferred_tools([tag_mcp_tool(mcp_secret)], enabled=True)


def test_subagent_reentry_does_not_touch_lead_state():
    lead_setup = build_deferred_tool_setup([active_tool, tag_mcp_tool(mcp_secret)], enabled=True)
    middleware = DeferredToolFilterMiddleware(lead_setup.deferred_names, lead_setup.catalog_hash)

    _ = build_deferred_tool_setup([tag_mcp_tool(mcp_secret)], enabled=True)

    class Request:
        def __init__(self):
            self.tools = [active_tool, mcp_secret]
            self.state = {"promoted": {"catalog_hash": lead_setup.catalog_hash, "names": ["mcp_secret"]}}

        def override(self, tools):
            self.tools = tools
            return self

    result = middleware._filter_tools(Request())
    assert {tool.name for tool in result.tools} == {"active_tool", "mcp_secret"}


def _make_skill(allowed_tools):
    return Skill(
        name="s",
        description="d",
        license="MIT",
        skill_dir=Path("/tmp/s"),
        skill_file=Path("/tmp/s/SKILL.md"),
        relative_path=Path("s"),
        category="public",
        allowed_tools=allowed_tools,
        enabled=True,
    )


def test_policy_denied_mcp_yields_no_tool_search_end_to_end():
    filtered = filter_tools_by_skill_allowed_tools([active_tool, tag_mcp_tool(mcp_secret)], [_make_skill(["active_tool"])])
    final_tools, setup = assemble_deferred_tools(filtered, enabled=True)

    assert [tool.name for tool in final_tools] == ["active_tool"]
    assert setup.deferred_names == frozenset()
    assert "tool_search" not in {tool.name for tool in final_tools}


def test_tool_search_appended_after_policy_but_never_exposes_denied_tool():
    allowed = ["active_tool", "mcp_secret"]
    filtered = filter_tools_by_skill_allowed_tools([active_tool, tag_mcp_tool(mcp_secret)], [_make_skill(allowed)])
    final_tools, setup = assemble_deferred_tools(filtered, enabled=True)

    assert "tool_search" in {tool.name for tool in final_tools}
    assert setup.deferred_names == frozenset({"mcp_secret"})
    assert set(setup.deferred_names) <= set(allowed)
