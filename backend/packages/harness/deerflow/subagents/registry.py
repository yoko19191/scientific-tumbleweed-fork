"""Subagent registry for managing available subagents."""

import logging
from dataclasses import replace
from typing import Any

from deerflow.sandbox.security import is_host_bash_allowed
from deerflow.subagents.builtins import BUILTIN_SUBAGENTS
from deerflow.subagents.config import SubagentConfig

logger = logging.getLogger(__name__)


def _resolve_subagents_app_config(app_config: Any | None = None):
    if app_config is None:
        from deerflow.config.subagents_config import get_subagents_app_config

        return get_subagents_app_config()
    return getattr(app_config, "subagents", app_config)


def _build_custom_subagent_config(name: str, *, app_config: Any | None = None) -> SubagentConfig | None:
    subagents_config = _resolve_subagents_app_config(app_config)
    custom = subagents_config.custom_agents.get(name)
    if custom is None:
        return None

    return SubagentConfig(
        name=name,
        description=custom.description,
        system_prompt=custom.system_prompt,
        tools=list(custom.tools) if custom.tools is not None else None,
        disallowed_tools=list(custom.disallowed_tools) if custom.disallowed_tools is not None else None,
        timeout_seconds=custom.timeout_seconds,
        max_turns=custom.max_turns,
        model=custom.model,
        skills=list(custom.skills) if custom.skills is not None else None,
    )


def get_subagent_config(name: str, *, app_config: Any | None = None) -> SubagentConfig | None:
    """Get a subagent configuration by name, with config.yaml overrides applied.

    Args:
        name: The name of the subagent.

    Returns:
        SubagentConfig if found (with any config.yaml overrides applied), None otherwise.
    """
    config = BUILTIN_SUBAGENTS.get(name)
    if config is None:
        config = _build_custom_subagent_config(name, app_config=app_config)
    if config is None:
        return None

    subagents_config = _resolve_subagents_app_config(app_config)
    is_builtin = name in BUILTIN_SUBAGENTS
    agent_override = subagents_config.agents.get(name)

    overrides = {}
    if agent_override is not None and agent_override.timeout_seconds is not None:
        effective_timeout = agent_override.timeout_seconds
    elif is_builtin:
        effective_timeout = subagents_config.timeout_seconds
    else:
        effective_timeout = config.timeout_seconds
    if effective_timeout != config.timeout_seconds:
        logger.debug(
            "Subagent '%s': timeout overridden by config.yaml (%ss -> %ss)",
            name,
            config.timeout_seconds,
            effective_timeout,
        )
        overrides["timeout_seconds"] = effective_timeout

    if agent_override is not None and agent_override.max_turns is not None:
        effective_max_turns = agent_override.max_turns
    elif is_builtin:
        effective_max_turns = subagents_config.get_max_turns_for(name, config.max_turns)
    else:
        effective_max_turns = config.max_turns
    if effective_max_turns != config.max_turns:
        logger.debug(
            "Subagent '%s': max_turns overridden by config.yaml (%s -> %s)",
            name,
            config.max_turns,
            effective_max_turns,
        )
        overrides["max_turns"] = effective_max_turns

    if agent_override is not None and agent_override.model is not None:
        effective_model = agent_override.model
    elif is_builtin:
        effective_model = subagents_config.get_model_for(name, config.model)
    else:
        effective_model = config.model
    if effective_model != config.model:
        logger.debug(
            "Subagent '%s': model overridden by config.yaml (%s -> %s)",
            name,
            config.model,
            effective_model,
        )
        overrides["model"] = effective_model
    effective_skills = subagents_config.get_skills_for(name)
    if effective_skills is not None and effective_skills != config.skills:
        logger.debug(
            "Subagent '%s': skills overridden by config.yaml (%s -> %s)",
            name,
            config.skills,
            effective_skills,
        )
        overrides["skills"] = effective_skills
    if overrides:
        config = replace(config, **overrides)

    return config


def list_subagents(*, app_config: Any | None = None) -> list[SubagentConfig]:
    """List all available subagent configurations (with config.yaml overrides applied).

    Returns:
        List of all registered SubagentConfig instances.
    """
    configs = []
    for name in get_subagent_names(app_config=app_config):
        config = get_subagent_config(name, app_config=app_config)
        if config is not None:
            configs.append(config)
    return configs


def get_subagent_names(*, app_config: Any | None = None) -> list[str]:
    """Get all available subagent names.

    Returns:
        List of subagent names.
    """
    names = list(BUILTIN_SUBAGENTS.keys())
    subagents_config = _resolve_subagents_app_config(app_config)
    for custom_name in subagents_config.custom_agents:
        if custom_name not in names:
            names.append(custom_name)
    return names


def get_available_subagent_names(*, app_config: Any | None = None) -> list[str]:
    """Get subagent names that should be exposed to the active runtime.

    Returns:
        List of subagent names visible to the current sandbox configuration.
    """
    names = get_subagent_names(app_config=app_config)
    try:
        host_bash_allowed = is_host_bash_allowed(app_config) if hasattr(app_config, "sandbox") else is_host_bash_allowed()
    except Exception:
        logger.debug("Could not determine host bash availability; exposing all subagents")
        return names

    if not host_bash_allowed:
        names = [name for name in names if name != "bash"]
    return names
