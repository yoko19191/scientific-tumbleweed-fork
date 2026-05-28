"""Tests for user-prefixed agent and user profile isolation."""

from pathlib import Path

import pytest
import yaml

from deerflow.config.agents_config import list_custom_agents, load_agent_config, load_agent_soul
from deerflow.config.storage_config import FilesystemStorageConfig, StorageConfig, set_storage_config
from deerflow.storage import reset_operators, user_agent_config_key, user_agent_soul_key, user_profile_key


@pytest.fixture
def storage_root(tmp_path: Path) -> Path:
    set_storage_config(StorageConfig(fs=FilesystemStorageConfig(root=str(tmp_path))))
    reset_operators()
    return tmp_path


def _create_agent(storage_root: Path, user_id: str | None, name: str, description: str = "", soul: str = "") -> None:
    config_path = storage_root / user_agent_config_key(user_id, name)
    soul_path = storage_root / user_agent_soul_key(user_id, name)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(yaml.dump({"name": name, "description": description}), encoding="utf-8")
    if soul:
        soul_path.write_text(soul, encoding="utf-8")


def test_agent_keys_user_scoped():
    user_a_key = user_agent_config_key("user-a", "test-agent")
    user_b_key = user_agent_config_key("user-b", "test-agent")
    global_key = user_agent_config_key(None, "test-agent")

    assert user_a_key == "custom-agents/user-a/test-agent/config.yaml"
    assert user_b_key == "custom-agents/user-b/test-agent/config.yaml"
    assert global_key == "custom-agents/__global__/test-agent/config.yaml"
    assert user_a_key != user_b_key
    assert user_a_key != global_key


def test_same_agent_name_different_users(storage_root):
    _create_agent(storage_root, "user-a", "my-agent", description="User A's agent", soul="User A soul")
    _create_agent(storage_root, "user-b", "my-agent", description="User B's agent", soul="User B soul")

    config_a = load_agent_config("my-agent", user_id="user-a")
    config_b = load_agent_config("my-agent", user_id="user-b")

    assert config_a is not None
    assert config_b is not None
    assert config_a.description == "User A's agent"
    assert config_b.description == "User B's agent"


def test_agent_soul_user_isolation(storage_root):
    _create_agent(storage_root, "user-a", "my-agent", soul="User A soul content")
    _create_agent(storage_root, "user-b", "my-agent", soul="User B soul content")

    soul_a = load_agent_soul("my-agent", user_id="user-a")
    soul_b = load_agent_soul("my-agent", user_id="user-b")

    assert soul_a == "User A soul content"
    assert soul_b == "User B soul content"
    assert soul_a != soul_b


def test_list_custom_agents_user_isolation(storage_root):
    _create_agent(storage_root, "user-a", "agent-alpha", description="Alpha for user A")
    _create_agent(storage_root, "user-a", "agent-beta", description="Beta for user A")
    _create_agent(storage_root, "user-b", "agent-gamma", description="Gamma for user B")

    agents_a = list_custom_agents(user_id="user-a")
    names_a = {a.name for a in agents_a}

    agents_b = list_custom_agents(user_id="user-b")
    names_b = {a.name for a in agents_b}

    assert "agent-alpha" in names_a
    assert "agent-beta" in names_a
    assert "agent-gamma" not in names_a

    assert "agent-gamma" in names_b
    assert "agent-alpha" not in names_b
    assert "agent-beta" not in names_b


def test_agent_not_found_for_other_user(storage_root):
    _create_agent(storage_root, "user-a", "private-agent", soul="Private soul")

    config_a = load_agent_config("private-agent", user_id="user-a")
    assert config_a is not None

    with pytest.raises(FileNotFoundError):
        load_agent_config("private-agent", user_id="user-b")


def test_user_md_user_isolation(storage_root):
    user_a_path = storage_root / user_profile_key("user-a")
    user_b_path = storage_root / user_profile_key("user-b")
    user_a_path.parent.mkdir(parents=True, exist_ok=True)
    user_b_path.parent.mkdir(parents=True, exist_ok=True)

    user_a_path.write_text("User A profile content", encoding="utf-8")
    user_b_path.write_text("User B profile content", encoding="utf-8")

    assert user_a_path != user_b_path
    assert user_a_path.read_text(encoding="utf-8") == "User A profile content"
    assert user_b_path.read_text(encoding="utf-8") == "User B profile content"


def test_user_md_key_user_scoped():
    user_a_key = user_profile_key("user-a")
    user_b_key = user_profile_key("user-b")

    assert user_a_key == "user-profile/user-a/USER.md"
    assert user_b_key == "user-profile/user-b/USER.md"
    assert user_a_key != user_b_key


def test_agent_soul_not_found_for_other_user(storage_root):
    _create_agent(storage_root, "user-a", "soul-agent", soul="Secret soul content")

    soul_a = load_agent_soul("soul-agent", user_id="user-a")
    assert soul_a == "Secret soul content"

    soul_b = load_agent_soul("soul-agent", user_id="user-b")
    assert soul_b is None
