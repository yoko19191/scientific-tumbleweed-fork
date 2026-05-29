import logging
from typing import Protocol, TypeVar

from deerflow.skills.types import Skill

logger = logging.getLogger(__name__)


class NamedTool(Protocol):
    name: str


ToolT = TypeVar("ToolT", bound=NamedTool)


def allowed_tool_names_for_skills(skills: list[Skill]) -> set[str] | None:
    """Return the union of explicit skill allowed-tools declarations.

    None means legacy allow-all behavior. It is returned only when no loaded
    skill declares allowed-tools. Once any skill declares the field, legacy
    skills without the field contribute no tools instead of disabling the
    explicit restrictions from other skills.
    """
    if not skills:
        return None

    allowed: set[str] = set()
    has_explicit_declaration = False
    for skill in skills:
        if skill.allowed_tools is None:
            continue
        has_explicit_declaration = True
        if not skill.allowed_tools:
            logger.info("Skill %s declared empty allowed-tools", skill.name)
        allowed.update(skill.allowed_tools)

    if not has_explicit_declaration:
        return None
    return allowed


def filter_tools_by_skill_allowed_tools(tools: list[ToolT], skills: list[Skill]) -> list[ToolT]:
    allowed = allowed_tool_names_for_skills(skills)
    if allowed is None:
        return tools

    available = {tool.name for tool in tools}
    unknown = allowed - available
    matched = allowed & available

    if not matched:
        # All declared allowed-tools are unknown to the runtime. Treat the
        # whole policy as misconfigured and fall back to allow-all so the
        # agent is not silently left with zero tools.
        offenders = sorted(skill.name for skill in skills if skill.allowed_tools and not (set(skill.allowed_tools) & available))
        logger.warning(
            "Skill allowed-tools policy matches no available tool — falling back to allow-all. "
            "Declared but unknown: %s. Offending skills: %s. Available tools: %s.",
            sorted(unknown),
            offenders,
            sorted(available),
        )
        return tools

    if unknown:
        logger.warning(
            "Skill allowed-tools references unknown tool name(s) that will be ignored: %s. Known tools: %s.",
            sorted(unknown),
            sorted(available),
        )

    return [tool for tool in tools if tool.name in matched]
