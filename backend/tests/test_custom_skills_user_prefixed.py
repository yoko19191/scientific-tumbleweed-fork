"""Tests for user-prefixed custom skill isolation (US-013)."""

import json
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from deerflow.skills.installer import install_skill_from_archive
from deerflow.skills.manager import (
    append_history,
    custom_skill_exists,
    get_custom_skill_dir,
    get_custom_skill_file,
    get_skill_history_file,
    read_custom_skill_content,
    read_history,
)


@pytest.fixture
def temp_skills_dir():
    """Create a temporary skills directory for testing."""
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


@pytest.fixture
def mock_paths(temp_skills_dir):
    """Mock Paths to use temporary directory."""
    with patch("deerflow.skills.manager.get_app_config") as mock_config:
        mock_app_config = MagicMock()
        mock_app_config.skills.get_skills_path.return_value = temp_skills_dir
        mock_config.return_value = mock_app_config

        with patch("deerflow.config.paths.get_paths") as mock_get_paths:
            mock_paths_obj = MagicMock()
            mock_paths_obj.user_skills_custom_dir.side_effect = lambda user_id: temp_skills_dir / "users" / user_id / "skills" / "custom"
            mock_paths_obj.user_extensions_config_file.side_effect = lambda user_id: temp_skills_dir / "users" / user_id / "extensions_config.json"
            mock_get_paths.return_value = mock_paths_obj
            yield mock_paths_obj


def test_custom_skill_dir_user_scoped(mock_paths, temp_skills_dir):
    """Test that custom skill directory is user-scoped when user_id is provided."""
    user_a_dir = get_custom_skill_dir("test-skill", user_id="user-a")
    user_b_dir = get_custom_skill_dir("test-skill", user_id="user-b")
    global_dir = get_custom_skill_dir("test-skill", user_id=None)

    assert "user-a" in str(user_a_dir)
    assert "user-b" in str(user_b_dir)
    assert "users" not in str(global_dir)
    assert user_a_dir != user_b_dir
    assert user_a_dir != global_dir


def test_custom_skill_file_user_scoped(mock_paths, temp_skills_dir):
    """Test that custom skill file path is user-scoped."""
    user_a_file = get_custom_skill_file("test-skill", user_id="user-a")
    user_b_file = get_custom_skill_file("test-skill", user_id="user-b")

    assert "user-a" in str(user_a_file)
    assert "user-b" in str(user_b_file)
    assert user_a_file != user_b_file
    assert user_a_file.name == "SKILL.md"
    assert user_b_file.name == "SKILL.md"


def test_skill_history_file_user_scoped(mock_paths, temp_skills_dir):
    """Test that skill history file is user-scoped."""
    user_a_history = get_skill_history_file("test-skill", user_id="user-a")
    user_b_history = get_skill_history_file("test-skill", user_id="user-b")

    assert "user-a" in str(user_a_history)
    assert "user-b" in str(user_b_history)
    assert user_a_history != user_b_history


def test_custom_skill_exists_user_isolation(mock_paths, temp_skills_dir):
    """Test that custom_skill_exists checks user-scoped paths."""
    # Create skill for user-a only
    user_a_file = get_custom_skill_file("test-skill", user_id="user-a")
    user_a_file.parent.mkdir(parents=True, exist_ok=True)
    user_a_file.write_text("---\nname: test-skill\n---\n# Test Skill", encoding="utf-8")

    assert custom_skill_exists("test-skill", user_id="user-a")
    assert not custom_skill_exists("test-skill", user_id="user-b")
    assert not custom_skill_exists("test-skill", user_id=None)


def test_read_custom_skill_content_user_isolation(mock_paths, temp_skills_dir):
    """Test that read_custom_skill_content reads from user-scoped paths."""
    # Create different content for two users
    user_a_file = get_custom_skill_file("test-skill", user_id="user-a")
    user_a_file.parent.mkdir(parents=True, exist_ok=True)
    user_a_file.write_text("---\nname: test-skill\n---\n# User A Content", encoding="utf-8")

    user_b_file = get_custom_skill_file("test-skill", user_id="user-b")
    user_b_file.parent.mkdir(parents=True, exist_ok=True)
    user_b_file.write_text("---\nname: test-skill\n---\n# User B Content", encoding="utf-8")

    content_a = read_custom_skill_content("test-skill", user_id="user-a")
    content_b = read_custom_skill_content("test-skill", user_id="user-b")

    assert "User A Content" in content_a
    assert "User B Content" in content_b
    assert content_a != content_b


def test_append_history_user_isolation(mock_paths, temp_skills_dir):
    """Test that append_history writes to user-scoped history files."""
    record_a = {"action": "test", "author": "user-a"}
    record_b = {"action": "test", "author": "user-b"}

    append_history("test-skill", record_a, user_id="user-a")
    append_history("test-skill", record_b, user_id="user-b")

    history_a = read_history("test-skill", user_id="user-a")
    history_b = read_history("test-skill", user_id="user-b")

    assert len(history_a) == 1
    assert len(history_b) == 1
    assert history_a[0]["author"] == "user-a"
    assert history_b[0]["author"] == "user-b"


def test_read_history_user_isolation(mock_paths, temp_skills_dir):
    """Test that read_history reads from user-scoped history files."""
    # Create history for user-a
    history_file_a = get_skill_history_file("test-skill", user_id="user-a")
    history_file_a.parent.mkdir(parents=True, exist_ok=True)
    history_file_a.write_text(json.dumps({"action": "edit", "author": "user-a"}) + "\n", encoding="utf-8")

    # Create history for user-b
    history_file_b = get_skill_history_file("test-skill", user_id="user-b")
    history_file_b.parent.mkdir(parents=True, exist_ok=True)
    history_file_b.write_text(json.dumps({"action": "delete", "author": "user-b"}) + "\n", encoding="utf-8")

    history_a = read_history("test-skill", user_id="user-a")
    history_b = read_history("test-skill", user_id="user-b")

    assert len(history_a) == 1
    assert len(history_b) == 1
    assert history_a[0]["action"] == "edit"
    assert history_b[0]["action"] == "delete"


def test_install_skill_user_scoped(mock_paths, temp_skills_dir):
    """Test that install_skill_from_archive installs to user-scoped directory."""
    # Create a minimal .skill archive
    with tempfile.TemporaryDirectory() as tmp:
        skill_dir = Path(tmp) / "test-skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text("---\nname: test-skill\ndescription: Test\n---\n# Test", encoding="utf-8")

        # Create the archive with correct path
        archive_base = Path(tmp) / "test-skill"
        shutil.make_archive(str(archive_base), "zip", skill_dir.parent, skill_dir.name)
        archive_path = archive_base.with_suffix(".skill")
        # Rename .zip to .skill
        Path(str(archive_base) + ".zip").rename(archive_path)

        # Install for user-a
        result_a = install_skill_from_archive(archive_path, user_id="user-a")
        assert result_a["success"]
        assert result_a["skill_name"] == "test-skill"

        # Verify installed to user-a's directory
        user_a_skill = get_custom_skill_file("test-skill", user_id="user-a")
        assert user_a_skill.exists()

        # Verify NOT in user-b's directory
        user_b_skill = get_custom_skill_file("test-skill", user_id="user-b")
        assert not user_b_skill.exists()


def test_same_skill_name_different_users(mock_paths, temp_skills_dir):
    """Test that two users can have custom skills with the same name."""
    # Create skill for user-a
    user_a_file = get_custom_skill_file("shared-name", user_id="user-a")
    user_a_file.parent.mkdir(parents=True, exist_ok=True)
    user_a_file.write_text("---\nname: shared-name\n---\n# User A Version", encoding="utf-8")

    # Create skill with same name for user-b
    user_b_file = get_custom_skill_file("shared-name", user_id="user-b")
    user_b_file.parent.mkdir(parents=True, exist_ok=True)
    user_b_file.write_text("---\nname: shared-name\n---\n# User B Version", encoding="utf-8")

    # Both should exist independently
    assert custom_skill_exists("shared-name", user_id="user-a")
    assert custom_skill_exists("shared-name", user_id="user-b")

    # Content should be different
    content_a = read_custom_skill_content("shared-name", user_id="user-a")
    content_b = read_custom_skill_content("shared-name", user_id="user-b")
    assert "User A Version" in content_a
    assert "User B Version" in content_b



@pytest.fixture
def temp_skills_dir():
    """Create a temporary skills directory for testing."""
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


@pytest.fixture
def mock_paths(temp_skills_dir):
    """Mock Paths to use temporary directory."""
    with patch("deerflow.skills.manager.get_app_config") as mock_config:
        mock_app_config = MagicMock()
        mock_app_config.skills.get_skills_path.return_value = temp_skills_dir
        mock_config.return_value = mock_app_config

        with patch("deerflow.config.paths.get_paths") as mock_get_paths:
            mock_paths_obj = MagicMock()
            mock_paths_obj.user_skills_custom_dir.side_effect = lambda user_id: temp_skills_dir / "users" / user_id / "skills" / "custom"
            mock_paths_obj.user_extensions_config_file.side_effect = lambda user_id: temp_skills_dir / "users" / user_id / "extensions_config.json"
            mock_get_paths.return_value = mock_paths_obj
            yield mock_paths_obj


def test_custom_skill_dir_user_scoped(mock_paths, temp_skills_dir):
    """Test that custom skill directory is user-scoped when user_id is provided."""
    user_a_dir = get_custom_skill_dir("test-skill", user_id="user-a")
    user_b_dir = get_custom_skill_dir("test-skill", user_id="user-b")
    global_dir = get_custom_skill_dir("test-skill", user_id=None)

    assert "user-a" in str(user_a_dir)
    assert "user-b" in str(user_b_dir)
    assert "users" not in str(global_dir)
    assert user_a_dir != user_b_dir
    assert user_a_dir != global_dir


def test_custom_skill_file_user_scoped(mock_paths, temp_skills_dir):
    """Test that custom skill file path is user-scoped."""
    user_a_file = get_custom_skill_file("test-skill", user_id="user-a")
    user_b_file = get_custom_skill_file("test-skill", user_id="user-b")

    assert "user-a" in str(user_a_file)
    assert "user-b" in str(user_b_file)
    assert user_a_file != user_b_file
    assert user_a_file.name == "SKILL.md"
    assert user_b_file.name == "SKILL.md"


def test_skill_history_file_user_scoped(mock_paths, temp_skills_dir):
    """Test that skill history file is user-scoped."""
    user_a_history = get_skill_history_file("test-skill", user_id="user-a")
    user_b_history = get_skill_history_file("test-skill", user_id="user-b")

    assert "user-a" in str(user_a_history)
    assert "user-b" in str(user_b_history)
    assert user_a_history != user_b_history


def test_custom_skill_exists_user_isolation(mock_paths, temp_skills_dir):
    """Test that custom_skill_exists checks user-scoped paths."""
    # Create skill for user-a only
    user_a_file = get_custom_skill_file("test-skill", user_id="user-a")
    user_a_file.parent.mkdir(parents=True, exist_ok=True)
    user_a_file.write_text("---\nname: test-skill\n---\n# Test Skill", encoding="utf-8")

    assert custom_skill_exists("test-skill", user_id="user-a")
    assert not custom_skill_exists("test-skill", user_id="user-b")
    assert not custom_skill_exists("test-skill", user_id=None)


def test_read_custom_skill_content_user_isolation(mock_paths, temp_skills_dir):
    """Test that read_custom_skill_content reads from user-scoped paths."""
    # Create different content for two users
    user_a_file = get_custom_skill_file("test-skill", user_id="user-a")
    user_a_file.parent.mkdir(parents=True, exist_ok=True)
    user_a_file.write_text("---\nname: test-skill\n---\n# User A Content", encoding="utf-8")

    user_b_file = get_custom_skill_file("test-skill", user_id="user-b")
    user_b_file.parent.mkdir(parents=True, exist_ok=True)
    user_b_file.write_text("---\nname: test-skill\n---\n# User B Content", encoding="utf-8")

    content_a = read_custom_skill_content("test-skill", user_id="user-a")
    content_b = read_custom_skill_content("test-skill", user_id="user-b")

    assert "User A Content" in content_a
    assert "User B Content" in content_b
    assert content_a != content_b


def test_append_history_user_isolation(mock_paths, temp_skills_dir):
    """Test that append_history writes to user-scoped history files."""
    record_a = {"action": "test", "author": "user-a"}
    record_b = {"action": "test", "author": "user-b"}

    append_history("test-skill", record_a, user_id="user-a")
    append_history("test-skill", record_b, user_id="user-b")

    history_a = read_history("test-skill", user_id="user-a")
    history_b = read_history("test-skill", user_id="user-b")

    assert len(history_a) == 1
    assert len(history_b) == 1
    assert history_a[0]["author"] == "user-a"
    assert history_b[0]["author"] == "user-b"


def test_read_history_user_isolation(mock_paths, temp_skills_dir):
    """Test that read_history reads from user-scoped history files."""
    # Create history for user-a
    history_file_a = get_skill_history_file("test-skill", user_id="user-a")
    history_file_a.parent.mkdir(parents=True, exist_ok=True)
    history_file_a.write_text(json.dumps({"action": "edit", "author": "user-a"}) + "\n", encoding="utf-8")

    # Create history for user-b
    history_file_b = get_skill_history_file("test-skill", user_id="user-b")
    history_file_b.parent.mkdir(parents=True, exist_ok=True)
    history_file_b.write_text(json.dumps({"action": "delete", "author": "user-b"}) + "\n", encoding="utf-8")

    history_a = read_history("test-skill", user_id="user-a")
    history_b = read_history("test-skill", user_id="user-b")

    assert len(history_a) == 1
    assert len(history_b) == 1
    assert history_a[0]["action"] == "edit"
    assert history_b[0]["action"] == "delete"


def test_install_skill_user_scoped(mock_paths, temp_skills_dir):
    """Test that install_skill_from_archive installs to user-scoped directory."""
    # Create a minimal .skill archive
    with tempfile.TemporaryDirectory() as tmp:
        skill_dir = Path(tmp) / "test-skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text("---\nname: test-skill\ndescription: Test\n---\n# Test", encoding="utf-8")

        # Create the archive with correct path
        archive_base = Path(tmp) / "test-skill"
        shutil.make_archive(str(archive_base), "zip", skill_dir.parent, skill_dir.name)
        archive_path = archive_base.with_suffix(".skill")
        # Rename .zip to .skill
        Path(str(archive_base) + ".zip").rename(archive_path)

        # Install for user-a
        result_a = install_skill_from_archive(archive_path, user_id="user-a")
        assert result_a["success"]
        assert result_a["skill_name"] == "test-skill"

        # Verify installed to user-a's directory
        user_a_skill = get_custom_skill_file("test-skill", user_id="user-a")
        assert user_a_skill.exists()

        # Verify NOT in user-b's directory
        user_b_skill = get_custom_skill_file("test-skill", user_id="user-b")
        assert not user_b_skill.exists()


def test_same_skill_name_different_users(mock_paths, temp_skills_dir):
    """Test that two users can have custom skills with the same name."""
    # Create skill for user-a
    user_a_file = get_custom_skill_file("shared-name", user_id="user-a")
    user_a_file.parent.mkdir(parents=True, exist_ok=True)
    user_a_file.write_text("---\nname: shared-name\n---\n# User A Version", encoding="utf-8")

    # Create skill with same name for user-b
    user_b_file = get_custom_skill_file("shared-name", user_id="user-b")
    user_b_file.parent.mkdir(parents=True, exist_ok=True)
    user_b_file.write_text("---\nname: shared-name\n---\n# User B Version", encoding="utf-8")

    # Both should exist independently
    assert custom_skill_exists("shared-name", user_id="user-a")
    assert custom_skill_exists("shared-name", user_id="user-b")

    # Content should be different
    content_a = read_custom_skill_content("shared-name", user_id="user-a")
    content_b = read_custom_skill_content("shared-name", user_id="user-b")
    assert "User A Version" in content_a
    assert "User B Version" in content_b


