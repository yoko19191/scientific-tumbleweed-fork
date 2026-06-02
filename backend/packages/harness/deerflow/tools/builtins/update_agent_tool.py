"""Tool for custom agents to persist safe self-updates."""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from langgraph.types import Command

from deerflow.config.agents_config import AgentConfig, CustomAgentStore, normalize_agent_name
from deerflow.config.app_config import get_app_config
from deerflow.runtime.user_context import resolve_runtime_user_id
from deerflow.tools.types import Runtime

logger = logging.getLogger(__name__)


def _message(content: str, runtime: Runtime) -> Command:
    return Command(update={"messages": [ToolMessage(content=content, tool_call_id=runtime.tool_call_id)]})


def _error(message: str, runtime: Runtime) -> Command:
    return _message(f"Error: {message}", runtime)


@tool(parse_docstring=True)
def update_agent(
    runtime: Runtime,
    soul: str | None = None,
    description: str | None = None,
    skills: list[str] | None = None,
    tool_groups: list[str] | None = None,
    model: str | None = None,
    variant: str | None = None,
) -> Command:
    """Persist updates to the current custom agent's SOUL.md and config.yaml.

    Use this when the user asks to refine the current custom agent's identity,
    description, skill whitelist, tool-group whitelist, default model, or
    chat/computer variant. Only
    fields explicitly passed are updated; omitted fields keep their existing
    values. Pass soul as the full replacement SOUL.md content.

    Args:
        soul: Optional full replacement SOUL.md content.
        description: Optional new one-line description.
        skills: Optional skill whitelist. [] means no skills; omit means unchanged.
        tool_groups: Optional tool-group whitelist. [] means empty; omit means unchanged.
        model: Optional model override, which must exist in config.yaml models.
        variant: Optional runtime variant, either "chat" or "computer".
    """
    if soul is None and description is None and skills is None and tool_groups is None and model is None and variant is None:
        return _error("No fields provided. Pass at least one of: soul, description, skills, tool_groups, model, variant.", runtime)

    agent_name_raw = runtime.context.get("agent_name") if runtime.context else None
    try:
        agent_name = normalize_agent_name(agent_name_raw) if agent_name_raw else None
    except ValueError as exc:
        return _error(str(exc), runtime)

    if not agent_name:
        return _error("update_agent is only available inside a custom agent chat with agent_name in runtime context.", runtime)

    user_id = resolve_runtime_user_id(runtime)

    if model is not None and get_app_config().get_model_config(model) is None:
        return _error(f"Unknown model '{model}'. Pass a model name that exists in config.yaml.", runtime)
    if variant is not None and variant not in {"chat", "computer"}:
        return _error("Invalid variant. Expected 'chat' or 'computer'.", runtime)

    store = CustomAgentStore()
    try:
        existing_cfg = store.load_config(agent_name, user_id=user_id)
    except FileNotFoundError:
        return _error(f"Agent '{agent_name}' does not exist for the current user. Use setup_agent to create it first.", runtime)
    except ValueError as exc:
        return _error(f"Agent '{agent_name}' has an unreadable config: {exc}", runtime)

    if existing_cfg is None:
        return _error(f"Agent '{agent_name}' could not be loaded.", runtime)

    updated_fields: list[str] = []
    config_data: dict[str, Any] = {"name": agent_name}

    new_description = description if description is not None else existing_cfg.description
    if new_description:
        config_data["description"] = new_description
    if description is not None and description != existing_cfg.description:
        updated_fields.append("description")

    new_model = model if model is not None else existing_cfg.model
    if new_model is not None:
        config_data["model"] = new_model
    if model is not None and model != existing_cfg.model:
        updated_fields.append("model")

    new_variant = variant if variant is not None else existing_cfg.variant
    if new_variant is not None:
        config_data["variant"] = new_variant
    if variant is not None and variant != existing_cfg.variant:
        updated_fields.append("variant")

    new_tool_groups = tool_groups if tool_groups is not None else existing_cfg.tool_groups
    if new_tool_groups is not None:
        config_data["tool_groups"] = new_tool_groups
    if tool_groups is not None and tool_groups != existing_cfg.tool_groups:
        updated_fields.append("tool_groups")

    new_skills = skills if skills is not None else existing_cfg.skills
    if new_skills is not None:
        config_data["skills"] = new_skills
    if skills is not None and skills != existing_cfg.skills:
        updated_fields.append("skills")

    existing_soul = store.load_soul(agent_name, user_id=user_id)
    soul_changed = soul is not None and soul != existing_soul
    if soul_changed:
        updated_fields.append("soul")

    if not updated_fields:
        return _message(f"No changes applied to agent '{agent_name}'. The provided values matched the existing configuration.", runtime)

    try:
        if any(field in updated_fields for field in ("description", "model", "variant", "tool_groups", "skills")):
            store.write_config(AgentConfig(**config_data), user_id=user_id)
        if soul_changed and soul is not None:
            store.write_soul(agent_name, soul, user_id=user_id)
    except Exception as exc:
        logger.error("[update_agent] Failed to update agent '%s' (user=%s): %s", agent_name, user_id, exc, exc_info=True)
        return _error(f"Failed to update agent '{agent_name}': {exc}", runtime)

    logger.info("[update_agent] Updated agent '%s' (user=%s) fields: %s", agent_name, user_id, updated_fields)
    return _message(
        f"Agent '{agent_name}' updated successfully. Changed: {', '.join(updated_fields)}. The new configuration takes effect on the next user turn.",
        runtime,
    )
