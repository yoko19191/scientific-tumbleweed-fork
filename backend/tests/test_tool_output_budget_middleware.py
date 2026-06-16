import re
from types import SimpleNamespace
from unittest.mock import MagicMock

from langchain_core.messages import AIMessage, ToolMessage
from langgraph.types import Command

from deerflow.agents.middlewares import tool_output_budget_middleware as budget_module
from deerflow.agents.middlewares.tool_output_budget_middleware import ToolOutputBudgetMiddleware, _message_text
from deerflow.config.app_config import AppConfig
from deerflow.config.sandbox_config import SandboxConfig
from deerflow.config.tool_output_config import ToolOutputConfig


def _request(*, outputs_path=None, sandbox_id=None, variant=None):
    state = {}
    if outputs_path is not None:
        state["thread_data"] = {"outputs_path": str(outputs_path)}
    if sandbox_id is not None:
        state["sandbox"] = {"sandbox_id": sandbox_id}
    return SimpleNamespace(
        runtime=SimpleNamespace(state=state, context={"sandbox_provider_variant": variant} if variant else {}),
        tool_call={"id": "tc-1", "name": "search"},
    )


def _message(content: str, *, name: str = "search") -> ToolMessage:
    return ToolMessage(content=content, tool_call_id="tc-1", name=name)


def _saved_virtual_path(content: str) -> str:
    match = re.search(r"saved to (/mnt/user-data/outputs/[^ ]+)", content)
    assert match is not None
    return match.group(1)


class FakeSandbox:
    def __init__(self) -> None:
        self.files: dict[str, str] = {}

    def execute_command(self, command: str) -> str:
        if command.startswith("test -s "):
            path = command.split(" ", 3)[2].strip("'")
            return "OK" if self.files.get(path) else "MISSING"
        return ""

    def write_file(self, path: str, content: str) -> None:
        self.files[path] = content


class FakeProvider:
    def __init__(self, sandbox: FakeSandbox, *, uses_thread_data_mounts: bool) -> None:
        self.sandbox = sandbox
        self.uses_thread_data_mounts = uses_thread_data_mounts
        self.requested_ids: list[str] = []

    def get(self, sandbox_id: str) -> FakeSandbox:
        self.requested_ids.append(sandbox_id)
        return self.sandbox


def test_message_text_extracts_plain_and_text_parts():
    assert _message_text("plain") == "plain"
    assert _message_text([{"text": "one"}, "two"]) == "one\ntwo"
    assert _message_text([{"type": "image_url"}]) is None
    assert _message_text({"text": "not a supported message content shape"}) is None


def test_app_config_parses_tool_output_section():
    cfg = AppConfig(
        sandbox=SandboxConfig(use="deerflow.sandbox.local:LocalSandboxProvider"),
        tool_output={"enabled": False, "externalize_min_chars": 42},
    )

    assert cfg.tool_output.enabled is False
    assert cfg.tool_output.externalize_min_chars == 42


def test_small_tool_output_passthrough():
    middleware = ToolOutputBudgetMiddleware(ToolOutputConfig(externalize_min_chars=100, fallback_max_chars=200))
    expected = _message("short")

    result = middleware.wrap_tool_call(_request(), lambda _req: expected)

    assert result is expected


def test_exempt_read_file_output_is_not_budgeted(tmp_path):
    middleware = ToolOutputBudgetMiddleware(ToolOutputConfig(externalize_min_chars=10, fallback_max_chars=20))
    expected = _message("x" * 200, name="read_file")

    result = middleware.wrap_tool_call(_request(outputs_path=tmp_path), lambda _req: expected)

    assert result is expected


def test_oversized_output_externalizes_to_thread_outputs(tmp_path):
    content = "A" * 80
    middleware = ToolOutputBudgetMiddleware(
        ToolOutputConfig(externalize_min_chars=20, preview_head_chars=5, preview_tail_chars=5, fallback_max_chars=120)
    )

    result = middleware.wrap_tool_call(_request(outputs_path=tmp_path), lambda _req: _message(content))

    assert isinstance(result, ToolMessage)
    virtual_path = _saved_virtual_path(result.content)
    saved = tmp_path / virtual_path.removeprefix("/mnt/user-data/outputs/")
    assert saved.read_text() == content
    assert result.content.startswith("AAAAA")
    assert result.content.endswith("AAAAA")


def test_mounted_sandbox_externalizes_to_thread_outputs(monkeypatch, tmp_path):
    content = "M" * 80
    sandbox = FakeSandbox()
    provider = FakeProvider(sandbox, uses_thread_data_mounts=True)

    def fake_get_sandbox_provider(*, variant=None):
        assert variant == "computer"
        return provider

    monkeypatch.setattr(budget_module, "get_sandbox_provider", fake_get_sandbox_provider)
    middleware = ToolOutputBudgetMiddleware(ToolOutputConfig(externalize_min_chars=20, fallback_max_chars=120))

    result = middleware.wrap_tool_call(
        _request(outputs_path=tmp_path, sandbox_id="sb-1", variant="computer"),
        lambda _req: _message(content),
    )

    virtual_path = _saved_virtual_path(result.content)
    saved = tmp_path / virtual_path.removeprefix("/mnt/user-data/outputs/")
    assert saved.read_text() == content
    assert provider.requested_ids == ["sb-1"]
    assert sandbox.files == {}


def test_remote_sandbox_externalizes_inside_sandbox(monkeypatch):
    content = "R" * 80
    sandbox = FakeSandbox()
    provider = FakeProvider(sandbox, uses_thread_data_mounts=False)

    def fake_get_sandbox_provider(*, variant=None):
        assert variant == "computer"
        return provider

    monkeypatch.setattr(budget_module, "get_sandbox_provider", fake_get_sandbox_provider)
    middleware = ToolOutputBudgetMiddleware(ToolOutputConfig(externalize_min_chars=20, fallback_max_chars=120))

    result = middleware.wrap_tool_call(
        _request(outputs_path="/host/not-mounted", sandbox_id="sb-remote", variant="computer"),
        lambda _req: _message(content),
    )

    virtual_path = _saved_virtual_path(result.content)
    assert sandbox.files[virtual_path] == content
    assert provider.requested_ids == ["sb-remote"]


def test_fallback_truncates_when_persistent_storage_unavailable():
    content = "0123456789" * 20
    middleware = ToolOutputBudgetMiddleware(
        ToolOutputConfig(
            externalize_min_chars=20,
            fallback_max_chars=180,
            fallback_head_chars=10,
            fallback_tail_chars=10,
        )
    )

    result = middleware.wrap_tool_call(_request(), lambda _req: _message(content))

    assert isinstance(result, ToolMessage)
    assert len(result.content) <= 180
    assert "Persistent storage unavailable" in result.content


def test_command_update_messages_are_budgeted(tmp_path):
    content = "C" * 80
    middleware = ToolOutputBudgetMiddleware(ToolOutputConfig(externalize_min_chars=20, fallback_max_chars=120))
    command = Command(update={"messages": [_message(content)]})

    result = middleware.wrap_tool_call(_request(outputs_path=tmp_path), lambda _req: command)

    assert isinstance(result, Command)
    patched = result.update["messages"][0]
    virtual_path = _saved_virtual_path(patched.content)
    saved = tmp_path / virtual_path.removeprefix("/mnt/user-data/outputs/")
    assert saved.read_text() == content


def test_wrap_model_call_budgets_historical_tool_messages():
    middleware = ToolOutputBudgetMiddleware(
        ToolOutputConfig(
            externalize_min_chars=20,
            fallback_max_chars=180,
            fallback_head_chars=10,
            fallback_tail_chars=10,
        )
    )
    request = MagicMock()
    request.messages = [AIMessage(content="ok"), _message("H" * 200)]
    patched_request = MagicMock()
    request.override.return_value = patched_request
    captured = []

    def handler(req):
        captured.append(req)
        return "model-response"

    result = middleware.wrap_model_call(request, handler)

    assert result == "model-response"
    request.override.assert_called_once()
    patched_messages = request.override.call_args.kwargs["messages"]
    assert "Persistent storage unavailable" in patched_messages[1].content
    assert captured == [patched_request]
