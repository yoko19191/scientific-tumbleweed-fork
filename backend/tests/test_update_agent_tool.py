"""Tests for update_agent tool."""

from __future__ import annotations

from unittest.mock import MagicMock

import yaml

from deerflow.config.storage_config import FilesystemStorageConfig, StorageConfig, set_storage_config
from deerflow.storage import reset_operators, user_agent_config_key, user_agent_soul_key
from deerflow.tools.builtins.update_agent_tool import update_agent


def _configure_storage(tmp_path):
    set_storage_config(StorageConfig(fs=FilesystemStorageConfig(root=str(tmp_path))))
    reset_operators()


def _runtime(agent_name: str | None = "test-agent", user_id: str = "user-1"):
    runtime = MagicMock()
    runtime.context = {"agent_name": agent_name, "user_id": user_id}
    runtime.tool_call_id = "tool-1"
    return runtime


def _write_agent(tmp_path, *, user_id: str = "user-1", name: str = "test-agent", soul: str = "old soul", config: dict | None = None):
    config_data = {"name": name, "description": "old description"}
    if config:
        config_data.update(config)
    config_path = tmp_path / user_agent_config_key(user_id, name)
    soul_path = tmp_path / user_agent_soul_key(user_id, name)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(yaml.dump(config_data, allow_unicode=True), encoding="utf-8")
    soul_path.write_text(soul, encoding="utf-8")


def test_update_agent_requires_agent_name(tmp_path):
    _configure_storage(tmp_path)
    result = update_agent.func(runtime=_runtime(agent_name=None), description="new")
    assert "only available inside a custom agent" in result.update["messages"][0].content


def test_update_agent_updates_soul_and_description(tmp_path):
    _configure_storage(tmp_path)
    _write_agent(tmp_path)

    result = update_agent.func(runtime=_runtime(), soul="new soul", description="new description")

    assert "updated successfully" in result.update["messages"][0].content
    assert (tmp_path / user_agent_soul_key("user-1", "test-agent")).read_text(encoding="utf-8") == "new soul"
    config = yaml.safe_load((tmp_path / user_agent_config_key("user-1", "test-agent")).read_text(encoding="utf-8"))
    assert config["description"] == "new description"


def test_update_agent_preserves_other_user_agent(tmp_path):
    _configure_storage(tmp_path)
    _write_agent(tmp_path, user_id="user-1", soul="user one")
    _write_agent(tmp_path, user_id="user-2", soul="user two")

    update_agent.func(runtime=_runtime(user_id="user-1"), soul="changed")

    assert (tmp_path / user_agent_soul_key("user-1", "test-agent")).read_text(encoding="utf-8") == "changed"
    assert (tmp_path / user_agent_soul_key("user-2", "test-agent")).read_text(encoding="utf-8") == "user two"


def test_update_agent_reports_noop(tmp_path):
    _configure_storage(tmp_path)
    _write_agent(tmp_path, soul="same", config={"description": "same desc", "skills": []})

    result = update_agent.func(runtime=_runtime(), soul="same", description="same desc", skills=[])

    assert "No changes applied" in result.update["messages"][0].content
