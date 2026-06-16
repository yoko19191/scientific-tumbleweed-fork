from types import SimpleNamespace

import pytest
from langchain_core.messages import ToolMessage
from langgraph.errors import GraphInterrupt

from deerflow.agents.middlewares import tool_error_handling_middleware as tool_error_module
from deerflow.agents.middlewares.safety_finish_reason_middleware import SafetyFinishReasonMiddleware
from deerflow.agents.middlewares.tool_error_handling_middleware import ToolErrorHandlingMiddleware
from deerflow.config.safety_finish_reason_config import SafetyFinishReasonConfig
from deerflow.config.tool_output_config import ToolOutputConfig


def _request(name: str = "web_search", tool_call_id: str | None = "tc-1"):
    tool_call = {"name": name}
    if tool_call_id is not None:
        tool_call["id"] = tool_call_id
    return SimpleNamespace(tool_call=tool_call)


def test_build_subagent_runtime_middlewares_appends_safety_finish_reason(monkeypatch):
    base = [ToolErrorHandlingMiddleware()]
    app_config = SimpleNamespace(safety_finish_reason=SafetyFinishReasonConfig(enabled=True))

    monkeypatch.setattr(tool_error_module, "_build_runtime_middlewares", lambda **_kwargs: list(base))
    monkeypatch.setattr("deerflow.config.app_config.get_app_config", lambda: app_config)

    middlewares = tool_error_module.build_subagent_runtime_middlewares(lazy_init=False)

    assert middlewares[:-1] == base
    assert isinstance(middlewares[-1], SafetyFinishReasonMiddleware)


def test_build_subagent_runtime_middlewares_appends_deferred_filter(monkeypatch):
    from langchain_core.tools import tool as as_tool

    from deerflow.agents.middlewares.deferred_tool_filter_middleware import DeferredToolFilterMiddleware
    from deerflow.tools.builtins.tool_search import build_deferred_tool_setup
    from deerflow.tools.mcp_metadata import tag_mcp_tool

    @as_tool
    def mcp_calc(expression: str) -> str:
        """Evaluate arithmetic."""
        return expression

    base = [ToolErrorHandlingMiddleware()]
    app_config = SimpleNamespace(safety_finish_reason=SafetyFinishReasonConfig(enabled=False))
    setup = build_deferred_tool_setup([tag_mcp_tool(mcp_calc)], enabled=True)

    monkeypatch.setattr(tool_error_module, "_build_runtime_middlewares", lambda **_kwargs: list(base))

    middlewares = tool_error_module.build_subagent_runtime_middlewares(
        lazy_init=False,
        app_config=app_config,
        deferred_setup=setup,
    )

    assert middlewares[:-1] == base
    assert isinstance(middlewares[-1], DeferredToolFilterMiddleware)


def test_build_lead_runtime_middlewares_starts_with_tool_output_budget(monkeypatch):
    monkeypatch.setattr(
        "deerflow.config.guardrails_config.get_guardrails_config",
        lambda: SimpleNamespace(enabled=False, provider=None),
    )
    app_config = SimpleNamespace(
        safety_finish_reason=SafetyFinishReasonConfig(enabled=False),
        tool_output=ToolOutputConfig(enabled=True),
    )

    middlewares = tool_error_module.build_lead_runtime_middlewares(lazy_init=False, app_config=app_config)

    assert [type(m).__name__ for m in middlewares[:4]] == [
        "ToolOutputBudgetMiddleware",
        "ThreadDataMiddleware",
        "UploadsMiddleware",
        "SandboxMiddleware",
    ]


def test_wrap_tool_call_passthrough_on_success():
    middleware = ToolErrorHandlingMiddleware()
    req = _request()
    expected = ToolMessage(content="ok", tool_call_id="tc-1", name="web_search")

    result = middleware.wrap_tool_call(req, lambda _req: expected)

    assert result is expected


def test_wrap_tool_call_returns_error_tool_message_on_exception():
    middleware = ToolErrorHandlingMiddleware()
    req = _request(name="web_search", tool_call_id="tc-42")

    def _boom(_req):
        raise RuntimeError("network down")

    result = middleware.wrap_tool_call(req, _boom)

    assert isinstance(result, ToolMessage)
    assert result.tool_call_id == "tc-42"
    assert result.name == "web_search"
    assert result.status == "error"
    assert "Tool 'web_search' failed" in result.text
    assert "network down" in result.text


def test_wrap_tool_call_uses_fallback_tool_call_id_when_missing():
    middleware = ToolErrorHandlingMiddleware()
    req = _request(name="mcp_tool", tool_call_id=None)

    def _boom(_req):
        raise ValueError("bad request")

    result = middleware.wrap_tool_call(req, _boom)

    assert isinstance(result, ToolMessage)
    assert result.tool_call_id == "missing_tool_call_id"
    assert result.name == "mcp_tool"
    assert result.status == "error"


def test_wrap_tool_call_reraises_graph_interrupt():
    middleware = ToolErrorHandlingMiddleware()
    req = _request(name="ask_clarification", tool_call_id="tc-int")

    def _interrupt(_req):
        raise GraphInterrupt(())

    with pytest.raises(GraphInterrupt):
        middleware.wrap_tool_call(req, _interrupt)


@pytest.mark.anyio
async def test_awrap_tool_call_returns_error_tool_message_on_exception():
    middleware = ToolErrorHandlingMiddleware()
    req = _request(name="mcp_tool", tool_call_id="tc-async")

    async def _boom(_req):
        raise TimeoutError("request timed out")

    result = await middleware.awrap_tool_call(req, _boom)

    assert isinstance(result, ToolMessage)
    assert result.tool_call_id == "tc-async"
    assert result.name == "mcp_tool"
    assert result.status == "error"
    assert "request timed out" in result.text


@pytest.mark.anyio
async def test_awrap_tool_call_reraises_graph_interrupt():
    middleware = ToolErrorHandlingMiddleware()
    req = _request(name="ask_clarification", tool_call_id="tc-int-async")

    async def _interrupt(_req):
        raise GraphInterrupt(())

    with pytest.raises(GraphInterrupt):
        await middleware.awrap_tool_call(req, _interrupt)
