"""Backward-compatible lead-agent facade.

Concrete implementation lives in ``base.py`` plus the variant entrypoints in
``chat.py`` and ``computer.py``. Keep this module importable while older tests
and runtime paths move to the semantic modules.
"""

from deerflow.agents.lead_agent.base import (
    _available_skill_names,
    _build_middlewares,
    _call_with_optional_app_config,
    _create_compaction_middleware,
    _create_guardrail_middleware,
    _create_hook_middleware,
    _create_permission_middleware,
    _create_summarization_middleware,
    _create_todo_list_middleware,
    _get_runtime_config,
    _load_enabled_skills_for_tool_policy,
    _resolve_effective_tool_groups,
    _resolve_model_name,
    _write_effective_runtime_context,
    build_lead_agent,
    create_agent,
    create_chat_model,
    get_app_config,
    load_agent_config,
)
from deerflow.agents.lead_agent.chat import make_chat_lead_agent
from deerflow.agents.lead_agent.computer import make_computer_lead_agent
from deerflow.agents.lead_agent.config import CHAT_PROFILE, CHAT_TOOL_GROUPS, COMPUTER_PROFILE, LeadProfile, get_lead_profile
from deerflow.agents.lead_agent.prompt import apply_prompt_template

__all__ = [
    "CHAT_PROFILE",
    "CHAT_TOOL_GROUPS",
    "COMPUTER_PROFILE",
    "LeadProfile",
    "_available_skill_names",
    "_build_middlewares",
    "_call_with_optional_app_config",
    "_create_compaction_middleware",
    "_create_guardrail_middleware",
    "_create_hook_middleware",
    "_create_permission_middleware",
    "_create_summarization_middleware",
    "_create_todo_list_middleware",
    "_get_runtime_config",
    "_load_enabled_skills_for_tool_policy",
    "_resolve_effective_tool_groups",
    "_resolve_model_name",
    "_write_effective_runtime_context",
    "apply_prompt_template",
    "build_lead_agent",
    "create_agent",
    "create_chat_model",
    "get_app_config",
    "get_lead_profile",
    "load_agent_config",
    "make_chat_lead_agent",
    "make_computer_lead_agent",
]
