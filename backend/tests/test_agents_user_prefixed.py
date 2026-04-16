"""Tests for user-prefixed agent and user profile isolation (US-015)."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from deerflow.config.agents_config import list_custom_agents, load_agent_config, load_agent_soul
from deerflow.config.paths import get_paths


@pytest.fixture
def temp_base_dir():
    """Create a temporary base directory for testing."""
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


@pytest.fixture
def mock_paths(temp_base_dir):
    """Mock get_paths to use temporary directory."""
    from deerflow.config.paths import Paths

    paths = Paths(base_dir=temp_base_dir)
    with patch("deerflow.config.agents_config.get_paths", return_value=paths), \
         patch("deerflow.config.paths.get_paths", return_value=paths):
        yield paths


def _create_agent(base_dir: Path, user_id: str | None, name: str, description: str = "", soul: str = "") -> Path:
    """Create an agent directory with config.yaml and optional SOUL.md."""
    from deerflow.config.paths import Paths

    paths = Paths(base_dir=base_dir)
    agent_dir = paths.resolve_agent_dir(name, user_id)
    agent_dir.mkdir(parents=True, exist_ok=True)

    config = {"name": name, "description": description}
    with open(agent_dir / "config.yaml", "w", encoding="utf-8") as f:
        yaml.dump(config, f)

    if soul:
        (agent_dir / "SOUL.md").write_text(soul, encoding="utf-8")

    return agent_dir


def test_agent_dir_user_scoped(mock_paths, temp_base_dir):
    """Test that agent directories are user-scoped when user_id is provided."""
    user_a_dir = mock_paths.resolve_agent_dir("test-agent", "user-a")
    user_b_dir = mock_paths.resolve_agent_dir("test-agent", "user-b")
    global_dir = mock_paths.resolve_agent_dir("test-agent", None)

    assert "user-a" in str(user_a_dir)
    assert "user-b" in str(user_b_dir)
    assert "users" not in str(global_dir)
    assert user_a_dir != user_b_dir
    assert user_a_dir != global_dir


def test_same_agent_name_different_users(mock_paths, temp_base_dir):
    """Test that two users can have agents with the same name."""
    _create_agent(temp_base_dir, "user-a", "my-agent", description="User A's agent", soul="User A soul")
    _create_agent(temp_base_dir, "user-b", "my-agent", description="User B's agent", soul="User B soul")

    # Load agent config for each user
    config_a = load_agent_config("my-agent", user_id="user-a")
    config_b = load_agent_config("my-agent", user_id="user-b")

    assert config_a is not None
    assert config_b is not None
    assert config_a.description == "User A's agent"
    assert config_b.description == "User B's agent"


def test_agent_soul_user_isolation(mock_paths, temp_base_dir):
    """Test that SOUL.md content is isolated per user."""
    _create_agent(temp_base_dir, "user-a", "my-agent", soul="User A soul content")
    _create_agent(temp_base_dir, "user-b", "my-agent", soul="User B soul content")

    soul_a = load_agent_soul("my-agent", user_id="user-a")
    soul_b = load_agent_soul("my-agent", user_id="user-b")

    assert soul_a == "User A soul content"
    assert soul_b == "User B soul content"
    assert soul_a != soul_b


def test_list_custom_agents_user_isolation(mock_paths, temp_base_dir):
    """Test that list_custom_agents returns only user-scoped agents."""
    # Create agents for user-a
    _create_agent(temp_base_dir, "user-a", "agent-alpha", description="Alpha for user A")
    _create_agent(temp_base_dir, "user-a", "agent-beta", description="Beta for user A")

    # Create agents for user-b
    _create_agent(temp_base_dir, "user-b", "agent-gamma", description="Gamma for user B")

    # List agents for user-a
    agents_a = list_custom_agents(user_id="user-a")
    names_a = {a.name for a in agents_a}

    # List agents for user-b
    agents_b = list_custom_agents(user_id="user-b")
    names_b = {a.name for a in agents_b}

    # User A should see their agents
    assert "agent-alpha" in names_a
    assert "agent-beta" in names_a
    assert "agent-gamma" not in names_a

    # User B should see their agents
    assert "agent-gamma" in names_b
    assert "agent-alpha" not in names_b
    assert "agent-beta" not in names_b


def test_agent_not_found_for_other_user(mock_paths, temp_base_dir):
    """Test that user B cannot access user A's agent."""
    _create_agent(temp_base_dir, "user-a", "private-agent", soul="Private soul")

    # User A can access their agent
    config_a = load_agent_config("private-agent", user_id="user-a")
    assert config_a is not None

    # User B cannot access user A's agent
    with pytest.raises(FileNotFoundError):
        load_agent_config("private-agent", user_id="user-b")


def test_user_md_user_isolation(mock_paths, temp_base_dir):
    """Test that USER.md is isolated per user."""
    # Create USER.md for user-a
    user_a_md = mock_paths.resolve_user_md("user-a")
    user_a_md.parent.mkdir(parents=True, exist_ok=True)
    user_a_md.write_text("User A profile content", encoding="utf-8")

    # Create USER.md for user-b
    user_b_md = mock_paths.resolve_user_md("user-b")
    user_b_md.parent.mkdir(parents=True, exist_ok=True)
    user_b_md.write_text("User B profile content", encoding="utf-8")

    # Verify paths are different
    assert user_a_md != user_b_md
    assert "user-a" in str(user_a_md)
    assert "user-b" in str(user_b_md)

    # Verify content is isolated
    assert user_a_md.read_text(encoding="utf-8") == "User A profile content"
    assert user_b_md.read_text(encoding="utf-8") == "User B profile content"


def test_user_md_path_user_scoped(mock_paths, temp_base_dir):
    """Test that resolve_user_md returns user-scoped path when user_id provided."""
    user_a_path = mock_paths.resolve_user_md("user-a")
    user_b_path = mock_paths.resolve_user_md("user-b")
    global_path = mock_paths.resolve_user_md(None)

    assert "user-a" in str(user_a_path)
    assert "user-b" in str(user_b_path)
    assert "users" not in str(global_path)
    assert user_a_path != user_b_path
    assert user_a_path != global_path


def test_agent_soul_not_found_for_other_user(mock_paths, temp_base_dir):
    """Test that user B cannot read user A's SOUL.md."""
    _create_agent(temp_base_dir, "user-a", "soul-agent", soul="Secret soul content")

    # User A can read their soul
    soul_a = load_agent_soul("soul-agent", user_id="user-a")
    assert soul_a == "Secret soul content"

    # User B gets None (agent doesn't exist for them)
    soul_b = load_agent_soul("soul-agent", user_id="user-b")
    assert soul_b is None
