import logging
import re
from pathlib import Path

import yaml

from .types import Skill

logger = logging.getLogger(__name__)


def parse_skill_file(skill_file: Path, category: str, relative_path: Path | None = None) -> Skill | None:
    """Parse a SKILL.md file and extract metadata.

    Args:
        skill_file: Path to the SKILL.md file.
        category: Category of the skill ('public' or 'custom').
        relative_path: Relative path from the category root to the skill
            directory.  Defaults to the skill directory name when omitted.

    Returns:
        Skill object if parsing succeeds, None otherwise.
    """
    if not skill_file.exists() or skill_file.name != "SKILL.md":
        return None

    try:
        content = skill_file.read_text(encoding="utf-8")

        # Extract YAML front-matter block between leading ``---`` fences.
        front_matter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
        if not front_matter_match:
            return None

        front_matter_text = front_matter_match.group(1)

        # Parse YAML front matter using yaml.safe_load for full YAML support
        # (handles multiline strings with | and > block scalars).
        # Falls back to simple key-value parsing if yaml.safe_load fails
        # (e.g. unquoted colons in values like "description: A skill: does things").
        metadata: dict | None = None
        try:
            parsed = yaml.safe_load(front_matter_text)
            if isinstance(parsed, dict):
                # Strip trailing whitespace from string values (yaml preserves trailing \n in block scalars)
                metadata = {k: v.rstrip() if isinstance(v, str) else v for k, v in parsed.items()}
        except yaml.YAMLError:
            pass

        if metadata is None:
            # Fallback: simple key-value parsing (handles unquoted colons)
            metadata = {}
            for line in front_matter_text.split("\n"):
                line_stripped = line.strip()
                if not line_stripped:
                    continue
                if ":" in line_stripped:
                    key, value = line_stripped.split(":", 1)
                    metadata[key.strip()] = value.strip()

        if not metadata:
            return None

        # Extract required fields
        name = metadata.get("name")
        description = metadata.get("description")

        if not name or not isinstance(name, str):
            return None
        if not description or not isinstance(description, str):
            return None

        # Normalise: strip surrounding whitespace that YAML may preserve.
        name = name.strip()
        description = description.strip()

        if not name or not description:
            return None

        license_text = metadata.get("license")
        if license_text is not None:
            license_text = str(license_text).strip() or None

        return Skill(
            name=name,
            description=description,
            license=license_text,
            skill_dir=skill_file.parent,
            skill_file=skill_file,
            relative_path=relative_path or Path(skill_file.parent.name),
            category=category,
            enabled=True,  # Actual state comes from the extensions config file.
        )

    except Exception:
        logger.exception("Unexpected error parsing skill file %s", skill_file)
        return None
