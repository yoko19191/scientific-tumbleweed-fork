"""Tests for deferred MCP tool loading via tool_search."""

import json
from types import SimpleNamespace

import pytest
from langchain_core.messages import ToolMessage
from langchain_core.tools import tool as langchain_tool
from langgraph.types import Command

from deerflow.config.tool_search_config import ToolSearchConfig, load_tool_search_config_from_dict
from deerflow.tools.builtins.tool_search import (
    DeferredToolCatalog,
    assemble_deferred_tools,
    build_deferred_tool_setup,
    build_tool_search_tool,
    get_deferred_tools_prompt_section,
)
from deerflow.tools.mcp_metadata import is_mcp_tool, tag_mcp_tool


def _make_mock_tool(name: str, description: str):
    @langchain_tool(name)
    def mock_tool(arg: str) -> str:
        """Mock tool."""
        return f"{name}: {arg}"

    mock_tool.description = description
    return mock_tool


@pytest.fixture
def catalog() -> DeferredToolCatalog:
    return DeferredToolCatalog(
        (
            _make_mock_tool("github_create_issue", "Create a new issue in a GitHub repository"),
            _make_mock_tool("github_list_repos", "List repositories for a GitHub user"),
            _make_mock_tool("slack_send_message", "Send a message to a Slack channel"),
            _make_mock_tool("slack_list_channels", "List available Slack channels"),
            _make_mock_tool("sentry_list_issues", "List issues from Sentry error tracking"),
            _make_mock_tool("database_query", "Execute a SQL query against the database"),
        )
    )


class TestToolSearchConfig:
    def test_default_disabled(self):
        assert ToolSearchConfig().enabled is False

    def test_enabled(self):
        assert ToolSearchConfig(enabled=True).enabled is True

    def test_load_from_dict(self):
        assert load_tool_search_config_from_dict({"enabled": True}).enabled is True

    def test_load_from_empty_dict(self):
        assert load_tool_search_config_from_dict({}).enabled is False


class TestDeferredToolCatalog:
    def test_names(self, catalog):
        assert "github_create_issue" in catalog.names
        assert "slack_send_message" in catalog.names
        assert len(catalog.names) == 6

    def test_search_select_single(self, catalog):
        results = catalog.search("select:github_create_issue")
        assert [tool.name for tool in results] == ["github_create_issue"]

    def test_search_select_multiple(self, catalog):
        results = catalog.search("select:github_create_issue,slack_send_message")
        assert {tool.name for tool in results} == {"github_create_issue", "slack_send_message"}

    def test_search_select_nonexistent(self, catalog):
        assert catalog.search("select:nonexistent_tool") == []

    def test_search_plus_keyword(self, catalog):
        results = catalog.search("+github")
        assert {tool.name for tool in results} == {"github_create_issue", "github_list_repos"}

    def test_search_plus_keyword_with_ranking(self, catalog):
        results = catalog.search("+github issue")
        assert len(results) == 2
        assert results[0].name == "github_create_issue"

    def test_search_regex_keyword(self, catalog):
        results = catalog.search("slack")
        assert {"slack_send_message", "slack_list_channels"} <= {tool.name for tool in results}

    def test_search_regex_description(self, catalog):
        results = catalog.search("SQL")
        assert [tool.name for tool in results] == ["database_query"]

    def test_search_regex_case_insensitive(self, catalog):
        assert len(catalog.search("GITHUB")) == 2

    def test_search_invalid_regex_falls_back_to_literal(self):
        calc = _make_mock_tool("calc", "Compute sum(a, b) expressions.")
        cat = DeferredToolCatalog((calc,))
        assert [tool.name for tool in cat.search("sum(")] == ["calc"]

    def test_search_empty_query_returns_empty(self, catalog):
        assert catalog.search("") == []
        assert catalog.search("   ") == []

    def test_search_bare_plus_returns_empty(self, catalog):
        assert catalog.search("+") == []
        assert catalog.search("+   ") == []

    def test_search_max_results(self):
        cat = DeferredToolCatalog(tuple(_make_mock_tool(f"tool_{i}", f"Tool number {i}") for i in range(10)))
        assert len(cat.search("tool")) <= 5

    def test_hash_stable_across_instances(self):
        a = _make_mock_tool("a_tool", "A")
        b = _make_mock_tool("b_tool", "B")
        assert DeferredToolCatalog((a, b)).hash == DeferredToolCatalog((b, a)).hash


class TestDeferredToolSetup:
    def test_metadata_tag(self):
        tool = _make_mock_tool("mcp_calc", "Calculate")
        assert is_mcp_tool(tool) is False
        assert is_mcp_tool(tag_mcp_tool(tool)) is True

    def test_setup_disabled_returns_empty(self):
        mcp_tool = tag_mcp_tool(_make_mock_tool("mcp_calc", "Calculate"))
        setup = build_deferred_tool_setup([mcp_tool], enabled=False)
        assert setup.tool_search_tool is None
        assert setup.deferred_names == frozenset()
        assert setup.catalog_hash is None

    def test_setup_no_mcp_returns_empty(self):
        setup = build_deferred_tool_setup([_make_mock_tool("local_echo", "Echo")], enabled=True)
        assert setup.tool_search_tool is None
        assert setup.deferred_names == frozenset()

    def test_setup_builds_from_mcp_survivors(self):
        mcp_tool = tag_mcp_tool(_make_mock_tool("mcp_calc", "Calculate"))
        setup = build_deferred_tool_setup([mcp_tool, _make_mock_tool("local_echo", "Echo")], enabled=True)
        assert setup.tool_search_tool is not None
        assert setup.tool_search_tool.name == "tool_search"
        assert setup.deferred_names == frozenset({"mcp_calc"})
        assert setup.catalog_hash

    def test_assemble_appends_tool_search_after_policy_filtering(self):
        mcp_tool = tag_mcp_tool(_make_mock_tool("mcp_calc", "Calculate"))
        local_tool = _make_mock_tool("local_echo", "Echo")
        final_tools, setup = assemble_deferred_tools([local_tool, mcp_tool], enabled=True)
        assert [tool.name for tool in final_tools] == ["local_echo", "mcp_calc", "tool_search"]
        assert setup.deferred_names == frozenset({"mcp_calc"})

    def test_tool_search_returns_command_with_hash_scoped_promotion(self):
        mcp_tool = _make_mock_tool("mcp_calc", "Calculate")
        catalog = DeferredToolCatalog((mcp_tool,))
        search_tool = build_tool_search_tool(catalog)

        result = search_tool.invoke(
            {
                "type": "tool_call",
                "name": "tool_search",
                "args": {"query": "select:mcp_calc"},
                "id": "call-1",
            }
        )

        assert isinstance(result, Command)
        assert result.update["promoted"] == {"catalog_hash": catalog.hash, "names": ["mcp_calc"]}
        msg = result.update["messages"][0]
        assert msg.tool_call_id == "call-1"
        assert msg.name == "tool_search"
        assert json.loads(msg.content)[0]["name"] == "mcp_calc"

    def test_tool_search_no_match_returns_empty_promotion(self):
        search_tool = build_tool_search_tool(DeferredToolCatalog((_make_mock_tool("mcp_calc", "Calculate"),)))
        result = search_tool.invoke(
            {
                "type": "tool_call",
                "name": "tool_search",
                "args": {"query": "select:not_found"},
                "id": "call-1",
            }
        )
        assert result.update["promoted"]["names"] == []
        assert "No tools found" in result.update["messages"][0].content


class TestDeferredToolsPromptSection:
    def test_empty_when_no_deferred_names(self):
        assert get_deferred_tools_prompt_section() == ""

    def test_lists_tool_names_only(self):
        section = get_deferred_tools_prompt_section(deferred_names=frozenset({"github_create_issue", "slack_send_message"}))
        assert "<available-deferred-tools>" in section
        assert "github_create_issue" in section
        assert "slack_send_message" in section
        assert "Create a new issue" not in section


class TestDeferredToolFilterMiddleware:
    def _middleware(self):
        from deerflow.agents.middlewares.deferred_tool_filter_middleware import DeferredToolFilterMiddleware

        return DeferredToolFilterMiddleware(frozenset({"github_create_issue", "slack_send_message"}), "hash-1")

    def test_filters_unpromoted_deferred_tools(self):
        active_tool = _make_mock_tool("my_active_tool", "An active tool")
        deferred_tool = _make_mock_tool("github_create_issue", "Deferred")

        class FakeRequest:
            def __init__(self, tools, state=None):
                self.tools = tools
                self.state = state or {}

            def override(self, **kwargs):
                return FakeRequest(kwargs.get("tools", self.tools), self.state)

        filtered = self._middleware()._filter_tools(FakeRequest([active_tool, deferred_tool]))
        assert [tool.name for tool in filtered.tools] == ["my_active_tool"]

    def test_promoted_tool_passes_when_hash_matches(self):
        active_tool = _make_mock_tool("my_active_tool", "An active tool")
        deferred_tool = _make_mock_tool("github_create_issue", "Deferred")

        class FakeRequest:
            def __init__(self, tools, state):
                self.tools = tools
                self.state = state

            def override(self, **kwargs):
                return FakeRequest(kwargs.get("tools", self.tools), self.state)

        state = {"promoted": {"catalog_hash": "hash-1", "names": ["github_create_issue"]}}
        filtered = self._middleware()._filter_tools(FakeRequest([active_tool, deferred_tool], state))
        assert {tool.name for tool in filtered.tools} == {"my_active_tool", "github_create_issue"}

    def test_stale_hash_keeps_tool_hidden(self):
        active_tool = _make_mock_tool("my_active_tool", "An active tool")
        deferred_tool = _make_mock_tool("github_create_issue", "Deferred")

        class FakeRequest:
            def __init__(self, tools):
                self.tools = tools
                self.state = {"promoted": {"catalog_hash": "stale", "names": ["github_create_issue"]}}

            def override(self, **kwargs):
                return FakeRequest(kwargs.get("tools", self.tools))

        filtered = self._middleware()._filter_tools(FakeRequest([active_tool, deferred_tool]))
        assert [tool.name for tool in filtered.tools] == ["my_active_tool"]

    def test_preserves_dict_tools(self):
        dict_tool = {"type": "function", "function": {"name": "provider_builtin"}}
        active_tool = _make_mock_tool("my_active_tool", "Active")

        class FakeRequest:
            def __init__(self, tools):
                self.tools = tools
                self.state = {}

            def override(self, **kwargs):
                return FakeRequest(kwargs.get("tools", self.tools))

        filtered = self._middleware()._filter_tools(FakeRequest([dict_tool, active_tool]))
        assert len(filtered.tools) == 2

    def test_unpromoted_deferred_tool_call_is_blocked(self):
        request = SimpleNamespace(tool_call={"name": "github_create_issue", "id": "call-1"}, state={})
        called = False

        def handler(_request):
            nonlocal called
            called = True
            return ToolMessage(content="executed", tool_call_id="call-1", name="github_create_issue")

        result = self._middleware().wrap_tool_call(request, handler)

        assert called is False
        assert isinstance(result, ToolMessage)
        assert result.status == "error"
        assert "tool_search" in result.content

    def test_promoted_deferred_tool_call_is_allowed(self):
        request = SimpleNamespace(
            tool_call={"name": "github_create_issue", "id": "call-1"},
            state={"promoted": {"catalog_hash": "hash-1", "names": ["github_create_issue"]}},
        )
        called = False

        def handler(_request):
            nonlocal called
            called = True
            return ToolMessage(content="executed", tool_call_id="call-1", name="github_create_issue")

        result = self._middleware().wrap_tool_call(request, handler)

        assert called is True
        assert isinstance(result, ToolMessage)
        assert result.content == "executed"

    @pytest.mark.anyio
    async def test_unpromoted_deferred_tool_call_is_blocked_async(self):
        request = SimpleNamespace(tool_call={"name": "github_create_issue", "id": "call-1"}, state={})
        called = False

        async def handler(_request):
            nonlocal called
            called = True
            return ToolMessage(content="executed", tool_call_id="call-1", name="github_create_issue")

        result = await self._middleware().awrap_tool_call(request, handler)
        assert called is False
        assert isinstance(result, ToolMessage)
        assert result.status == "error"
