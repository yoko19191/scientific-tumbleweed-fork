"""Tests for user-prefixed skill enablement (US-014)."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from deerflow.skills.loader import load_skills


@pytest.fixture
def temp_skills_dir():
    """Create a temporary skills directory for testing."""
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


@pytest.fixture
def mock_paths_and_config(temp_skills_dir):
    """Mock Paths and config to use temporary directory."""
    with patch("deerflow.config.paths.get_paths") as mock_get_paths:
        mock_paths_obj = MagicMock()
        mock_paths_obj.user_extensions_config_file.side_effect = lambda user_id: temp_skills_dir / "users" / user_id / "extensions_config.json"
        mock_paths_obj.user_skills_custom_dir.side_effect = lambda user_id: temp_skills_dir / "users" / user_id / "skills" / "custom"
        mock_get_paths.return_value = mock_paths_obj
        yield mock_paths_obj


def _write_skill(skill_dir: Path, name: str, description: str) -> None:
    """Write a minimal SKILL.md for tests."""
    skill_dir.mkdir(parents=True, exist_ok=True)
    content = f"---\nname: {name}\ndescription: {description}\n---\n\n# {name}\n"
    (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")


def test_load_skills_uses_user_scoped_extensions_config(mock_paths_and_config, temp_skills_dir):
    """Test that load_skills reads user-scoped extensions config when user_id provided."""
    # Create two public skills
    _write_skill(temp_skills_dir / "public" / "skill-a", "skill-a", "Skill A")
    _write_skill(temp_skills_dir / "public" / "skill-b", "skill-b", "Skill B")

    # User A disables skill-a
    user_a_config_path = temp_skills_dir / "users" / "user-a" / "extensions_config.json"
    user_a_config_path.parent.mkdir(parents=True, exist_ok=True)
    user_a_config_path.write_text(json.dumps({"skills": {"skill-a": {"enabled": False}}}), encoding="utf-8")

    # User B disables skill-b
    user_b_config_path = temp_skills_dir / "users" / "user-b" / "extensions_config.json"
    user_b_config_path.parent.mkdir(parents=True, exist_ok=True)
    user_b_config_path.write_text(json.dumps({"skills": {"skill-b": {"enabled": False}}}), encoding="utf-8")

    # Load skills for user-a (enabled_only=True) using explicit skills_path
    skills_a = load_skills(skills_path=temp_skills_dir, use_config=False, enabled_only=True, user_id="user-a")
    names_a = {skill.name for skill in skills_a}

    # Load skills for user-b (enabled_only=True) using explicit skills_path
    skills_b = load_skills(skills_path=temp_skills_dir, use_config=False, enabled_only=True, user_id="user-b")
    names_b = {skill.name for skill in skills_b}

    # User A should see skill-b but not skill-a
    assert "skill-b" in names_a
    assert "skill-a" not in names_a

    # User B should see skill-a but not skill-b
    assert "skill-a" in names_b
    assert "skill-b" not in names_b


def test_load_skills_user_a_disabling_skill_does_not_affect_user_b(mock_paths_and_config, temp_skills_dir):
    """Test that user A disabling a skill does not disable it for user B."""
    # Create a public skill
    _write_skill(temp_skills_dir / "public" / "shared-skill", "shared-skill", "Shared Skill")

    # User A disables the skill
    user_a_config_path = temp_skills_dir / "users" / "user-a" / "extensions_config.json"
    user_a_config_path.parent.mkdir(parents=True, exist_ok=True)
    user_a_config_path.write_text(json.dumps({"skills": {"shared-skill": {"enabled": False}}}), encoding="utf-8")

    # Load skills for user-a (enabled_only=True)
    skills_a = load_skills(skills_path=temp_skills_dir, use_config=False, enabled_only=True, user_id="user-a")
    names_a = {skill.name for skill in skills_a}

    # Load skills for user-b (enabled_only=True, no config)
    skills_b = load_skills(skills_path=temp_skills_dir, use_config=False, enabled_only=True, user_id="user-b")
    names_b = {skill.name for skill in skills_b}

    # User A should not see the skill
    assert "shared-skill" not in names_a

    # User B should see the skill (default enabled)
    assert "shared-skill" in names_b


def test_load_skills_enabled_state_independent_per_user(mock_paths_and_config, temp_skills_dir):
    """Test that skill enabled state is independent per user."""
    # Create three public skills
    _write_skill(temp_skills_dir / "public" / "skill-1", "skill-1", "Skill 1")
    _write_skill(temp_skills_dir / "public" / "skill-2", "skill-2", "Skill 2")
    _write_skill(temp_skills_dir / "public" / "skill-3", "skill-3", "Skill 3")

    # User A enables only skill-1 and skill-2
    user_a_config_path = temp_skills_dir / "users" / "user-a" / "extensions_config.json"
    user_a_config_path.parent.mkdir(parents=True, exist_ok=True)
    user_a_config_path.write_text(
        json.dumps({"skills": {"skill-1": {"enabled": True}, "skill-2": {"enabled": True}, "skill-3": {"enabled": False}}}),
        encoding="utf-8",
    )

    # User B enables only skill-2 and skill-3
    user_b_config_path = temp_skills_dir / "users" / "user-b" / "extensions_config.json"
    user_b_config_path.parent.mkdir(parents=True, exist_ok=True)
    user_b_config_path.write_text(
        json.dumps({"skills": {"skill-1": {"enabled": False}, "skill-2": {"enabled": True}, "skill-3": {"enabled": True}}}),
        encoding="utf-8",
    )

    # Load enabled skills for each user
    skills_a = load_skills(skills_path=temp_skills_dir, use_config=False, enabled_only=True, user_id="user-a")
    names_a = {skill.name for skill in skills_a}

    skills_b = load_skills(skills_path=temp_skills_dir, use_config=False, enabled_only=True, user_id="user-b")
    names_b = {skill.name for skill in skills_b}

    # Verify user A's enabled skills
    assert "skill-1" in names_a
    assert "skill-2" in names_a
    assert "skill-3" not in names_a

    # Verify user B's enabled skills
    assert "skill-1" not in names_b
    assert "skill-2" in names_b
    assert "skill-3" in names_b


def test_load_skills_with_user_id_none_uses_global_config(mock_paths_and_config, temp_skills_dir):
    """Test that load_skills with user_id=None uses global extensions config."""
    # Create a public skill
    _write_skill(temp_skills_dir / "public" / "global-skill", "global-skill", "Global Skill")

    # Create global extensions config that disables the skill
    global_config_path = temp_skills_dir / "extensions_config.json"
    global_config_path.write_text(json.dumps({"skills": {"global-skill": {"enabled": False}}}), encoding="utf-8")

    # Mock ExtensionsConfig.resolve_config_path to return our global config
    with patch("deerflow.config.extensions_config.ExtensionsConfig.resolve_config_path", return_value=global_config_path):
        # Load skills without user_id (should use global config)
        skills_global = load_skills(enabled_only=True, user_id=None)
        names_global = {skill.name for skill in skills_global}

        # Should not see the skill (disabled in global config)
        assert "global-skill" not in names_global


def test_get_skills_prompt_section_uses_user_id(mock_paths_and_config, temp_skills_dir):
    """Test that get_skills_prompt_section passes user_id to load_skills."""
    from deerflow.agents.lead_agent.prompt import get_skills_prompt_section

    # Create two public skills
    _write_skill(temp_skills_dir / "public" / "prompt-skill-a", "prompt-skill-a", "Prompt Skill A")
    _write_skill(temp_skills_dir / "public" / "prompt-skill-b", "prompt-skill-b", "Prompt Skill B")

    # User A disables prompt-skill-a
    user_a_config_path = temp_skills_dir / "users" / "user-a" / "extensions_config.json"
    user_a_config_path.parent.mkdir(parents=True, exist_ok=True)
    user_a_config_path.write_text(json.dumps({"skills": {"prompt-skill-a": {"enabled": False}}}), encoding="utf-8")

    # Mock load_skills to use our temp dir
    with patch("deerflow.agents.lead_agent.prompt.load_skills") as mock_load:
        # Simulate user-scoped loading
        from deerflow.skills.loader import load_skills as real_load_skills
        mock_load.side_effect = lambda **kwargs: real_load_skills(skills_path=temp_skills_dir, use_config=False, **kwargs)

        # Get skills prompt section for user-a
        get_skills_prompt_section(user_id="user-a")

        # Verify load_skills was called with user_id
        mock_load.assert_called_once_with(enabled_only=True, user_id="user-a")


def test_skill_enabled_state_in_skill_object(mock_paths_and_config, temp_skills_dir):
    """Test that Skill objects have correct enabled state based on user config."""
    # Create a public skill
    _write_skill(temp_skills_dir / "public" / "test-skill", "test-skill", "Test Skill")

    # User A disables the skill
    user_a_config_path = temp_skills_dir / "users" / "user-a" / "extensions_config.json"
    user_a_config_path.parent.mkdir(parents=True, exist_ok=True)
    user_a_config_path.write_text(json.dumps({"skills": {"test-skill": {"enabled": False}}}), encoding="utf-8")

    # Load all skills (enabled_only=False) for user-a
    skills_a = load_skills(skills_path=temp_skills_dir, use_config=False, enabled_only=False, user_id="user-a")
    test_skill_a = next((s for s in skills_a if s.name == "test-skill"), None)

    # Load all skills (enabled_only=False) for user-b
    skills_b = load_skills(skills_path=temp_skills_dir, use_config=False, enabled_only=False, user_id="user-b")
    test_skill_b = next((s for s in skills_b if s.name == "test-skill"), None)

    # Verify enabled state
    assert test_skill_a is not None
    assert test_skill_a.enabled is False

    assert test_skill_b is not None
    assert test_skill_b.enabled is True  # Default enabled
