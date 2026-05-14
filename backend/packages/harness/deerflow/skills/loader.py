import logging
import os
from pathlib import Path

from .parser import parse_skill_file
from .types import Skill

logger = logging.getLogger(__name__)


def get_skills_root_path() -> Path:
    """
    Get the root path of the skills directory.

    Returns:
        Path to the skills directory (deer-flow/skills)
    """
    # loader.py lives at packages/harness/deerflow/skills/loader.py — 5 parents up reaches backend/
    backend_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
    # skills directory is sibling to backend directory
    skills_dir = backend_dir.parent / "skills"
    return skills_dir


def load_skills(skills_path: Path | None = None, use_config: bool = True, enabled_only: bool = False, user_id: str | None = None) -> list[Skill]:
    """
    Load all skills from the skills directory.

    Scans both public and custom skill directories, parsing SKILL.md files
    to extract metadata. When *user_id* is provided, custom skills are loaded
    from the user-scoped directory and the enable/disable state is read from
    the user-scoped extensions config.

    Args:
        skills_path: Optional custom path to skills directory.
                     If not provided and use_config is True, uses path from config.
                     Otherwise defaults to deer-flow/skills
        use_config: Whether to load skills path from config (default: True)
        enabled_only: If True, only return enabled skills (default: False)
        user_id: If provided, loads custom skills and enable state from user-scoped paths.

    Returns:
        List of Skill objects, sorted by name
    """
    if skills_path is None:
        if use_config:
            try:
                from deerflow.config import get_app_config

                config = get_app_config()
                skills_path = config.skills.get_skills_path()
            except Exception:
                # Fallback to default if config fails
                skills_path = get_skills_root_path()
        else:
            skills_path = get_skills_root_path()

    skills_by_name: dict[str, Skill] = {}

    if not skills_path.exists():
        pass
    else:
        # When user_id is set, public skills come from the global path,
        # custom skills come from the user-scoped directory.
        if user_id:
            from deerflow.config.paths import get_paths

            scan_dirs = [
                ("public", skills_path / "public"),
                ("custom", get_paths().user_skills_custom_dir(user_id)),
            ]
        else:
            scan_dirs = [
                ("public", skills_path / "public"),
                ("custom", skills_path / "custom"),
            ]

        for category, category_path in scan_dirs:
            if not category_path.exists() or not category_path.is_dir():
                continue

            for current_root, dir_names, file_names in os.walk(category_path, followlinks=True):
                # Keep traversal deterministic and skip hidden directories.
                dir_names[:] = sorted(name for name in dir_names if not name.startswith("."))
                if "SKILL.md" not in file_names:
                    continue

                skill_file = Path(current_root) / "SKILL.md"
                relative_path = skill_file.parent.relative_to(category_path)

                skill = parse_skill_file(skill_file, category=category, relative_path=relative_path)
                if skill:
                    skills_by_name[skill.name] = skill

    skills = list(skills_by_name.values())

    # Load skills state configuration and update enabled status.
    # When user_id is set, read the per-user override from object storage
    # (OpenDAL) and merge it on top of the global config.
    try:
        import json as _json

        import opendal.exceptions as _opendal_exc

        from deerflow.config.extensions_config import ExtensionsConfig
        from deerflow.storage import get_operator, user_extensions_override_key

        if user_id:
            try:
                operator = get_operator()
                raw = bytes(operator.read(user_extensions_override_key(user_id)))
                user_data = _json.loads(raw.decode("utf-8"))
                if not isinstance(user_data, dict):
                    user_data = None
            except (_opendal_exc.NotFound, FileNotFoundError):
                user_data = None
            except Exception:
                logger.warning("Failed to read per-user extensions override; falling back to global", exc_info=True)
                user_data = None

            if user_data:
                extensions_config = ExtensionsConfig.from_dict(user_data)
            else:
                extensions_config = ExtensionsConfig.from_file()
        else:
            extensions_config = ExtensionsConfig.from_file()

        for skill in skills:
            skill.enabled = extensions_config.is_skill_enabled(skill.name, skill.category)
    except Exception as e:
        # If config loading fails, default to all enabled
        logger.warning("Failed to load extensions config: %s", e)

    # Filter by enabled status if requested
    if enabled_only:
        skills = [skill for skill in skills if skill.enabled]

    # Sort by name for consistent ordering
    skills.sort(key=lambda s: s.name)

    return skills
