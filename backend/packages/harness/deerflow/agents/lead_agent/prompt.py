import logging

from deerflow.agents._shared import call_with_optional_app_config as _call_with_optional_app_config
from deerflow.agents.lead_agent import dynamic_sections, skills_cache, skills_prompt
from deerflow.prompts.factory import PromptContext, build_prompt

logger = logging.getLogger(__name__)

_ENABLED_SKILLS_REFRESH_WAIT_TIMEOUT_SECONDS = skills_cache.ENABLED_SKILLS_REFRESH_WAIT_TIMEOUT_SECONDS
_enabled_skills_lock = skills_cache._enabled_skills_lock
_enabled_skills_cache = skills_cache._enabled_skills_cache
_enabled_skills_by_config_cache = skills_cache._enabled_skills_by_config_cache
_enabled_skills_refresh_active = skills_cache._enabled_skills_refresh_active
_enabled_skills_refresh_version = skills_cache._enabled_skills_refresh_version
_enabled_skills_refresh_event = skills_cache._enabled_skills_refresh_event
_load_enabled_skills_sync = skills_cache._load_enabled_skills_sync
_ensure_enabled_skills_cache = skills_cache._ensure_enabled_skills_cache
_get_enabled_skills = skills_cache._get_enabled_skills
get_cached_enabled_skills = skills_cache.get_cached_enabled_skills
get_enabled_skills_for_config = skills_cache.get_enabled_skills_for_config
_get_cached_skills_prompt_section = skills_prompt._get_cached_skills_prompt_section
get_skills_prompt_section = skills_prompt.get_skills_prompt_section
_build_subagent_section = dynamic_sections.build_subagent_section
get_agent_soul = dynamic_sections.get_agent_soul
get_deferred_tools_prompt_section = dynamic_sections.get_deferred_tools_prompt_section
_build_acp_section = dynamic_sections.build_acp_section
_build_custom_mounts_section = dynamic_sections.build_custom_mounts_section
_build_clarification_section = dynamic_sections.build_clarification_section
_build_working_directory_section = dynamic_sections.build_working_directory_section
_build_self_update_section = dynamic_sections.build_self_update_section
_build_citations_section = dynamic_sections.build_citations_section


def _invalidate_enabled_skills_cache():
    _get_cached_skills_prompt_section.cache_clear()
    return skills_cache._invalidate_enabled_skills_cache()


def prime_enabled_skills_cache() -> None:
    _ensure_enabled_skills_cache()


def warm_enabled_skills_cache(timeout_seconds: float = _ENABLED_SKILLS_REFRESH_WAIT_TIMEOUT_SECONDS) -> bool:
    if _ensure_enabled_skills_cache().wait(timeout=timeout_seconds):
        return True

    logger.warning("Timed out waiting %.1fs for enabled skills cache warm-up", timeout_seconds)
    return False


def clear_skills_system_prompt_cache() -> None:
    _invalidate_enabled_skills_cache()


async def refresh_skills_system_prompt_cache_async() -> None:
    _get_cached_skills_prompt_section.cache_clear()
    await skills_cache.refresh_enabled_skills_cache_async()


def _reset_skills_system_prompt_cache_state() -> None:
    _get_cached_skills_prompt_section.cache_clear()
    skills_cache._reset_skills_system_prompt_cache_state()


def _refresh_enabled_skills_cache() -> None:
    """Backward-compatible test helper for direct synchronous reload."""
    skills_cache._refresh_enabled_skills_cache()


def _get_memory_context(user_id: str | None = None) -> str:
    """Get memory context for injection into system prompt.

    Args:
        user_id: If provided, loads per-user memory. If None, loads global memory.

    Returns:
        Formatted memory context string wrapped in XML tags, or empty string if disabled.
    """
    try:
        from deerflow.agents.memory import format_memory_for_injection, get_memory_data
        from deerflow.config.memory_config import get_memory_config

        config = get_memory_config()
        if not config.enabled or not config.injection_enabled:
            return ""

        memory_data = get_memory_data(user_id)
        memory_content = format_memory_for_injection(memory_data, max_tokens=config.max_injection_tokens)

        if not memory_content.strip():
            return ""

        return f"""<memory>
{memory_content}
</memory>
"""
    except Exception as e:
        logger.error("Failed to load memory context: %s", e)
        return ""


def _apply_prompt_via_builder(
    subagent_enabled: bool = False,
    max_concurrent_subagents: int = 3,
    *,
    agent_key: str = "computer_lead",
    agent_name: str | None = None,
    user_id: str | None = None,
    available_skills: set[str] | None = None,
    tone_style: str = "normal",
    app_config=None,
) -> str:
    """Build system prompt using the unified Jinja2 prompt factory."""

    # Soul
    soul = get_agent_soul(agent_name, user_id=user_id)

    # Memory
    memory = _get_memory_context(user_id)

    # Skills
    skills = _call_with_optional_app_config(get_skills_prompt_section, available_skills, user_id=user_id, app_config=app_config)

    # Deferred tools
    deferred = _call_with_optional_app_config(get_deferred_tools_prompt_section, app_config=app_config)

    # Subagent section
    subagent_section = ""
    has_specialized_agents = False
    if subagent_enabled:
        n = max_concurrent_subagents
        subagent_section = _call_with_optional_app_config(
            _build_subagent_section,
            n,
            app_config=app_config,
            bash_available=agent_key != "chat_lead",
        )
        has_specialized_agents = True

    # Clarification system (included as a dynamic section)
    clarification_section = _build_clarification_section()

    # Working directory
    acp_section = _call_with_optional_app_config(_build_acp_section, app_config=app_config)
    custom_mounts_section = _call_with_optional_app_config(_build_custom_mounts_section, app_config=app_config)
    acp_and_mounts = "\n".join(s for s in (acp_section, custom_mounts_section) if s)
    working_directory_section = _build_working_directory_section(acp_and_mounts)

    # Citations
    citations_section = _build_citations_section()

    self_update_section = _build_self_update_section(agent_name)

    return build_prompt(
        agent_key,
        PromptContext(
            variant=agent_key.removesuffix("_lead"),
            agent_name=agent_name,
            tone_style=tone_style,  # type: ignore[arg-type]
            soul=soul,
            memory=memory,
            skills_section=skills,
            deferred_tools_section=deferred,
            subagent_section=subagent_section,
            subagent_enabled=subagent_enabled,
            clarification_section=clarification_section,
            working_directory_section=working_directory_section,
            citations_section=citations_section,
            self_update_section=self_update_section,
            has_verification=has_specialized_agents,
            has_explore=has_specialized_agents,
            has_plan=has_specialized_agents,
        ),
    )


def apply_prompt_template(
    subagent_enabled: bool = False,
    max_concurrent_subagents: int = 3,
    *,
    agent_key: str = "computer_lead",
    agent_name: str | None = None,
    user_id: str | None = None,
    available_skills: set[str] | None = None,
    tone_style: str = "normal",
    app_config=None,
) -> str:
    """Build the lead agent system prompt.

    Uses the unified Jinja2 prompt factory with the static/dynamic cache
    boundary preserved by ``build_prompt``.
    """
    return _apply_prompt_via_builder(
        subagent_enabled=subagent_enabled,
        max_concurrent_subagents=max_concurrent_subagents,
        agent_key=agent_key,
        agent_name=agent_name,
        user_id=user_id,
        available_skills=available_skills,
        tone_style=tone_style,
        app_config=app_config,
    )
