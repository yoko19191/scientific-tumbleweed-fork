import os
from pathlib import Path

from pydantic import BaseModel, Field


def _default_repo_root() -> Path:
    """Resolve the repo root without relying on the current working directory."""
    return Path(__file__).resolve().parents[5]


def _legacy_skills_candidates() -> tuple[Path, ...]:
    """Return source-tree skills locations for monorepo compatibility."""
    return (_default_repo_root() / "skills",)


def _project_root() -> Path:
    """Return the caller project root used for relative skills paths."""
    if env_root := os.getenv("DEER_FLOW_PROJECT_ROOT"):
        return Path(env_root).expanduser().resolve()
    return Path.cwd().resolve()


def _resolve_path(value: str) -> Path:
    """Resolve a configured skills path relative to the caller project root."""
    path = Path(value).expanduser()
    if path.is_absolute():
        return path.resolve()
    return (_project_root() / path).resolve()


class SkillsConfig(BaseModel):
    """Configuration for skills system"""

    path: str | None = Field(
        default=None,
        description=("Path to skills directory. If not specified, defaults to `skills` under the caller project root, falling back to the legacy repo-root location for monorepo compatibility."),
    )
    container_path: str = Field(
        default="/mnt/skills",
        description="Path where skills are mounted in the sandbox container",
    )

    def get_skills_path(self) -> Path:
        """
        Get the resolved skills directory path.

        Resolution order:
            1. Explicit ``path`` field
            2. ``DEER_FLOW_SKILLS_PATH`` environment variable
            3. ``skills`` under the caller project root (``project_root()``)
            4. Legacy repo-root candidates for monorepo compatibility (``_legacy_skills_candidates``)

        When none of (3) or (4) exist on disk, the project-root default is returned so callers
        can still surface a stable "no skills" location without raising.
        """
        if self.path:
            # Use configured path (can be absolute or relative to project root)
            return _resolve_path(self.path)
        if env_path := os.getenv("DEER_FLOW_SKILLS_PATH"):
            return _resolve_path(env_path)

        project_default = _project_root() / "skills"
        if project_default.is_dir():
            return project_default

        for candidate in _legacy_skills_candidates():
            if candidate.is_dir():
                return candidate

        return project_default

    def get_skill_container_path(self, skill_name: str, category: str = "public") -> str:
        """
        Get the full container path for a specific skill.

        Args:
            skill_name: Name of the skill (directory name)
            category: Category of the skill (public or custom)

        Returns:
            Full path to the skill in the container
        """
        return f"{self.container_path}/{category}/{skill_name}"
