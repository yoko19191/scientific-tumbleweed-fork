"""Tests for setup_agent tool — validates agent name security and data loss prevention."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from deerflow.config.storage_config import FilesystemStorageConfig, StorageConfig, set_storage_config
from deerflow.storage import reset_operators, user_agent_config_key, user_agent_soul_key
from deerflow.tools.builtins.setup_agent_tool import setup_agent

# --- Helpers ---


class _DummyRuntime(SimpleNamespace):
    context: dict
    tool_call_id: str


def _make_runtime(agent_name: str | None = "test-agent") -> MagicMock:
    runtime = MagicMock()
    runtime.context = {"agent_name": agent_name, "user_id": "user-1"}
    runtime.tool_call_id = "call_1"
    return runtime


def _configure_storage(tmp_path):
    set_storage_config(StorageConfig(fs=FilesystemStorageConfig(root=str(tmp_path))))
    reset_operators()


def _call_setup_agent(tmp_path, soul: str, description: str, agent_name: str = "test-agent"):
    """Call the underlying setup_agent function directly, bypassing langchain tool wrapper."""
    _configure_storage(tmp_path)
    return setup_agent.func(
        soul=soul,
        description=description,
        runtime=_make_runtime(agent_name),
    )


# --- Agent name validation tests ---


def test_setup_agent_rejects_invalid_agent_name_before_writing(tmp_path):
    _configure_storage(tmp_path)
    outside_dir = tmp_path.parent / "outside-target"
    traversal_agent = f"../../../{outside_dir.name}/evil"
    runtime = _DummyRuntime(context={"agent_name": traversal_agent, "user_id": "user-1"}, tool_call_id="tool-1")

    result = setup_agent.func(soul="test soul", description="desc", runtime=runtime)

    messages = result.update["messages"]
    assert len(messages) == 1
    assert "Invalid agent name" in messages[0].content
    assert not (tmp_path / "custom-agents").exists()
    assert not (outside_dir / "evil" / "SOUL.md").exists()


def test_setup_agent_rejects_absolute_agent_name_before_writing(tmp_path):
    _configure_storage(tmp_path)
    absolute_agent = str(tmp_path / "outside-agent")
    runtime = _DummyRuntime(context={"agent_name": absolute_agent, "user_id": "user-1"}, tool_call_id="tool-2")

    result = setup_agent.func(soul="test soul", description="desc", runtime=runtime)

    messages = result.update["messages"]
    assert len(messages) == 1
    assert "Invalid agent name" in messages[0].content
    assert not (tmp_path / "custom-agents").exists()


# --- Data loss prevention tests ---


class TestSetupAgentNoDataLoss:
    """Ensure setup_agent does not overwrite existing object-store agents."""

    def test_existing_agent_preserved(self, tmp_path):
        _configure_storage(tmp_path)
        _call_setup_agent(tmp_path, soul="original soul content", description="old")

        result = setup_agent.func(
            soul="new soul",
            description="desc",
            runtime=_make_runtime(),
        )

        messages = result.update["messages"]
        assert "already exists" in messages[0].content
        soul_path = tmp_path / user_agent_soul_key("user-1", "test-agent")
        assert soul_path.read_text(encoding="utf-8") == "original soul content"

    def test_new_agent_objects_cleaned_up_on_failure(self, tmp_path):
        _configure_storage(tmp_path)

        with patch("deerflow.tools.builtins.setup_agent_tool.yaml.dump", side_effect=OSError("write error")):
            setup_agent.func(
                soul="new soul",
                description="desc",
                runtime=_make_runtime(),
            )

        assert not (tmp_path / user_agent_config_key("user-1", "test-agent")).exists()
        assert not (tmp_path / user_agent_soul_key("user-1", "test-agent")).exists()

    def test_successful_setup_creates_files(self, tmp_path):
        """Happy path: setup_agent creates config.yaml and SOUL.md."""
        _call_setup_agent(tmp_path, soul="# My Agent", description="A test agent")

        assert (tmp_path / user_agent_soul_key("user-1", "test-agent")).read_text(encoding="utf-8") == "# My Agent"
        assert (tmp_path / user_agent_config_key("user-1", "test-agent")).exists()
