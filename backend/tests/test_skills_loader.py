"""Tests for recursive skills loading."""

from pathlib import Path

from deerflow.config import skills_config as skills_config_module
from deerflow.config.skills_config import SkillsConfig
from deerflow.skills.loader import get_skills_root_path, load_skills


def _write_skill(skill_dir: Path, name: str, description: str) -> None:
    """Write a minimal SKILL.md for tests."""
    skill_dir.mkdir(parents=True, exist_ok=True)
    content = f"---\nname: {name}\ndescription: {description}\n---\n\n# {name}\n"
    (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")


def test_get_skills_root_path_points_to_project_root_skills():
    """get_skills_root_path() should point to deer-flow/skills (sibling of backend/), not backend/packages/skills."""
    path = get_skills_root_path()
    assert path.name == "skills", f"Expected 'skills', got '{path.name}'"
    assert (path.parent / "backend").is_dir(), f"Expected skills path's parent to be project root containing 'backend/', but got {path}"


def test_skills_config_points_to_current_project_skills(tmp_path: Path, monkeypatch):
    """SkillsConfig should prefer the caller project's skills directory."""
    monkeypatch.delenv("DEER_FLOW_SKILLS_PATH", raising=False)
    monkeypatch.delenv("DEER_FLOW_PROJECT_ROOT", raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "skills").mkdir()

    assert SkillsConfig().get_skills_path() == tmp_path / "skills"


def test_skills_config_honors_env_override(tmp_path: Path, monkeypatch):
    """DEER_FLOW_SKILLS_PATH should override the caller project skills directory."""
    skills_root = tmp_path / "team-skills"
    monkeypatch.setenv("DEER_FLOW_SKILLS_PATH", str(skills_root))

    assert SkillsConfig().get_skills_path() == skills_root


def test_skills_config_falls_back_to_legacy_repo_skills(tmp_path: Path, monkeypatch):
    """When cwd lacks skills, preserve the monorepo repo-root fallback."""
    monkeypatch.delenv("DEER_FLOW_SKILLS_PATH", raising=False)
    monkeypatch.delenv("DEER_FLOW_PROJECT_ROOT", raising=False)
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    legacy_skills = tmp_path / "legacy-repo" / "skills"
    legacy_skills.mkdir(parents=True)
    monkeypatch.chdir(cwd)
    monkeypatch.setattr(skills_config_module, "_legacy_skills_candidates", lambda: (legacy_skills,))

    assert SkillsConfig().get_skills_path() == legacy_skills


def test_load_skills_discovers_nested_skills_and_sets_container_paths(tmp_path: Path):
    """Nested skills should be discovered recursively with correct container paths."""
    skills_root = tmp_path / "skills"

    _write_skill(skills_root / "public" / "root-skill", "root-skill", "Root skill")
    _write_skill(skills_root / "public" / "parent" / "child-skill", "child-skill", "Child skill")
    _write_skill(skills_root / "custom" / "team" / "helper", "team-helper", "Team helper")

    skills = load_skills(skills_path=skills_root, use_config=False, enabled_only=False)
    by_name = {skill.name: skill for skill in skills}

    assert {"root-skill", "child-skill", "team-helper"} <= set(by_name)

    root_skill = by_name["root-skill"]
    child_skill = by_name["child-skill"]
    team_skill = by_name["team-helper"]

    assert root_skill.skill_path == "root-skill"
    assert root_skill.get_container_file_path() == "/mnt/skills/public/root-skill/SKILL.md"

    assert child_skill.skill_path == "parent/child-skill"
    assert child_skill.get_container_file_path() == "/mnt/skills/public/parent/child-skill/SKILL.md"

    assert team_skill.skill_path == "team/helper"
    assert team_skill.get_container_file_path() == "/mnt/skills/custom/team/helper/SKILL.md"


def test_load_skills_skips_hidden_directories(tmp_path: Path):
    """Hidden directories should be excluded from recursive discovery."""
    skills_root = tmp_path / "skills"

    _write_skill(skills_root / "public" / "visible" / "ok-skill", "ok-skill", "Visible skill")
    _write_skill(
        skills_root / "public" / "visible" / ".hidden" / "secret-skill",
        "secret-skill",
        "Hidden skill",
    )

    skills = load_skills(skills_path=skills_root, use_config=False, enabled_only=False)
    names = {skill.name for skill in skills}

    assert "ok-skill" in names
    assert "secret-skill" not in names


def test_load_skills_prefers_custom_over_public_with_same_name(tmp_path: Path):
    skills_root = tmp_path / "skills"
    _write_skill(skills_root / "public" / "shared-skill", "shared-skill", "Public version")
    _write_skill(skills_root / "custom" / "shared-skill", "shared-skill", "Custom version")

    skills = load_skills(skills_path=skills_root, use_config=False, enabled_only=False)
    shared = next(skill for skill in skills if skill.name == "shared-skill")

    assert shared.category == "custom"
    assert shared.description == "Custom version"
