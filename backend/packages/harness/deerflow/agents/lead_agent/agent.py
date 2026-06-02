"""Lead agent factory.

Tracing callbacks are attached at the graph invocation root in
``make_chat_lead_agent`` and ``make_computer_lead_agent``. In-graph model calls
in this module, and in middleware reached by these graphs, should pass
``attach_tracing=False`` so Langfuse can lift reserved metadata onto the root
trace without duplicate model-level spans.
"""

import logging
from typing import TYPE_CHECKING

from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware
from langchain_core.runnables import RunnableConfig

from deerflow.agents.lead_agent.prompt import apply_prompt_template
from deerflow.agents.memory.summarization_hook import memory_flush_hook
from deerflow.agents.middleware_builder import build_ordered_middleware_chain
from deerflow.agents.middlewares.clarification_middleware import ClarificationMiddleware
from deerflow.agents.middlewares.dangling_tool_call_middleware import DanglingToolCallMiddleware
from deerflow.agents.middlewares.dynamic_context_middleware import DynamicContextMiddleware
from deerflow.agents.middlewares.llm_error_handling_middleware import LLMErrorHandlingMiddleware
from deerflow.agents.middlewares.loop_detection_middleware import LoopDetectionMiddleware
from deerflow.agents.middlewares.memory_middleware import MemoryMiddleware
from deerflow.agents.middlewares.safety_finish_reason_middleware import SafetyFinishReasonMiddleware
from deerflow.agents.middlewares.sandbox_audit_middleware import SandboxAuditMiddleware
from deerflow.agents.middlewares.subagent_limit_middleware import SubagentLimitMiddleware
from deerflow.agents.middlewares.summarization_middleware import (
    BeforeSummarizationHook,
    DeerFlowSummarizationMiddleware,
)
from deerflow.agents.middlewares.thread_data_middleware import ThreadDataMiddleware
from deerflow.agents.middlewares.title_middleware import TitleMiddleware
from deerflow.agents.middlewares.todo_middleware import TodoMiddleware
from deerflow.agents.middlewares.token_usage_middleware import TokenUsageMiddleware
from deerflow.agents.middlewares.tool_error_handling_middleware import ToolErrorHandlingMiddleware
from deerflow.agents.middlewares.uploads_middleware import UploadsMiddleware
from deerflow.agents.middlewares.view_image_middleware import ViewImageMiddleware
from deerflow.agents.thread_state import ThreadState
from deerflow.config.agents_config import load_agent_config, validate_agent_name
from deerflow.config.app_config import AppConfig, get_app_config
from deerflow.config.memory_config import get_memory_config
from deerflow.config.summarization_config import get_summarization_config
from deerflow.models import create_chat_model
from deerflow.sandbox.middleware import SandboxMiddleware
from deerflow.skills.tool_policy import filter_tools_by_skill_allowed_tools
from deerflow.skills.types import Skill
from deerflow.tracing import build_tracing_callbacks

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

CHAT_TOOL_GROUPS = ["web", "academic_search", "file:read", "file:write"]
VARIANT_DEFAULTS = {
    "chat": {
        "is_plan_mode": True,
        "subagent_enabled": True,
        "max_concurrent_subagents": 3,
        "tool_groups": CHAT_TOOL_GROUPS,
        "sandbox_provider_variant": "chat",
        "agent_key": "chat_lead",
    },
    "computer": {
        "is_plan_mode": True,
        "subagent_enabled": True,
        "max_concurrent_subagents": 5,
        "tool_groups": None,
        "sandbox_provider_variant": "computer",
        "agent_key": "computer_lead",
    },
}


def _get_runtime_config(config: RunnableConfig) -> dict:
    """Merge legacy configurable options with LangGraph runtime context."""
    cfg = dict(config.get("configurable", {}) or {})
    context = config.get("context", {}) or {}
    if isinstance(context, dict):
        cfg.update(context)
    return cfg


def _call_with_optional_app_config(func, *args, app_config: AppConfig | None = None, **kwargs):
    if app_config is None:
        return func(*args, **kwargs)
    try:
        return func(*args, app_config=app_config, **kwargs)
    except TypeError as exc:
        if "app_config" not in str(exc):
            raise
        return func(*args, **kwargs)


def _resolve_model_name(requested_model_name: str | None = None, *, app_config: AppConfig | None = None) -> str:
    """Resolve a runtime model name safely, falling back to default if invalid. Returns None if no models are configured."""
    app_config = app_config or get_app_config()
    default_model_name = app_config.models[0].name if app_config.models else None
    if default_model_name is None:
        raise ValueError("No chat models are configured. Please configure at least one model in config.yaml.")

    if requested_model_name and app_config.get_model_config(requested_model_name):
        return requested_model_name

    if requested_model_name and requested_model_name != default_model_name:
        logger.warning(f"Model '{requested_model_name}' not found in config; fallback to default model '{default_model_name}'.")
    return default_model_name


def _create_summarization_middleware(*, app_config: AppConfig | None = None) -> DeerFlowSummarizationMiddleware | None:
    """Create and configure the summarization middleware from config."""
    resolved_app_config = app_config
    config = resolved_app_config.summarization if resolved_app_config is not None else get_summarization_config()

    if not config.enabled:
        return None

    # Prepare trigger parameter
    trigger = None
    if config.trigger is not None:
        if isinstance(config.trigger, list):
            trigger = [t.to_tuple() for t in config.trigger]
        else:
            trigger = config.trigger.to_tuple()

    # Prepare keep parameter
    keep = config.keep.to_tuple()

    # Prepare model parameter
    if config.model_name:
        model = _call_with_optional_app_config(create_chat_model, name=config.model_name, thinking_enabled=False, attach_tracing=False, app_config=resolved_app_config)
    else:
        # Use a lightweight model for summarization to save costs
        # Falls back to default model if not explicitly specified
        model = _call_with_optional_app_config(create_chat_model, thinking_enabled=False, attach_tracing=False, app_config=resolved_app_config)

    # Prepare kwargs
    kwargs = {
        "model": model,
        "trigger": trigger,
        "keep": keep,
    }

    if config.trim_tokens_to_summarize is not None:
        kwargs["trim_tokens_to_summarize"] = config.trim_tokens_to_summarize

    if config.summary_prompt is not None:
        kwargs["summary_prompt"] = config.summary_prompt

    hooks: list[BeforeSummarizationHook] = []
    memory_config = resolved_app_config.memory if resolved_app_config is not None else get_memory_config()
    if memory_config.enabled:
        hooks.append(memory_flush_hook)

    # The logic below relies on two assumptions holding true: this factory is
    # the sole entry point for DeerFlowSummarizationMiddleware, and the runtime
    # config is not expected to change after startup.
    try:
        skills_container_path = (resolved_app_config or get_app_config()).skills.container_path or "/mnt/skills"
    except Exception:
        logger.exception("Failed to resolve skills container path; falling back to default")
        skills_container_path = "/mnt/skills"

    return DeerFlowSummarizationMiddleware(
        **kwargs,
        skills_container_path=skills_container_path,
        skill_file_read_tool_names=config.skill_file_read_tool_names,
        before_summarization=hooks,
        preserve_recent_skill_count=config.preserve_recent_skill_count,
        preserve_recent_skill_tokens=config.preserve_recent_skill_tokens,
        preserve_recent_skill_tokens_per_skill=config.preserve_recent_skill_tokens_per_skill,
    )


def _create_todo_list_middleware(is_plan_mode: bool) -> TodoMiddleware | None:
    """Create and configure the TodoList middleware.

    Args:
        is_plan_mode: Whether to enable plan mode with TodoList middleware.

    Returns:
        TodoMiddleware instance if plan mode is enabled, None otherwise.
    """
    if not is_plan_mode:
        return None

    # Custom prompts matching Scientific Tumbleweed's style
    system_prompt = """
<todo_list_system>
You have access to the `write_todos` tool to help you manage and track complex multi-step objectives.

**CRITICAL RULES:**
- Mark todos as completed IMMEDIATELY after finishing each step - do NOT batch completions
- Keep EXACTLY ONE task as `in_progress` at any time (unless tasks can run in parallel)
- Update the todo list in REAL-TIME as you work - this gives users visibility into your progress
- DO NOT use this tool for simple tasks (< 3 steps) - just complete them directly

**When to Use:**
This tool is designed for complex objectives that require systematic tracking:
- Complex multi-step tasks requiring 3+ distinct steps
- Non-trivial tasks needing careful planning and execution
- User explicitly requests a todo list
- User provides multiple tasks (numbered or comma-separated list)
- The plan may need revisions based on intermediate results

**When NOT to Use:**
- Single, straightforward tasks
- Trivial tasks (< 3 steps)
- Purely conversational or informational requests
- Simple tool calls where the approach is obvious

**Best Practices:**
- Break down complex tasks into smaller, actionable steps
- Use clear, descriptive task names
- Remove tasks that become irrelevant
- Add new tasks discovered during implementation
- Don't be afraid to revise the todo list as you learn more

**Task Management:**
Writing todos takes time and tokens - use it when helpful for managing complex problems, not for simple requests.
</todo_list_system>
"""

    tool_description = """Use this tool to create and manage a structured task list for complex work sessions.

**IMPORTANT: Only use this tool for complex tasks (3+ steps). For simple requests, just do the work directly.**

## When to Use

Use this tool in these scenarios:
1. **Complex multi-step tasks**: When a task requires 3 or more distinct steps or actions
2. **Non-trivial tasks**: Tasks requiring careful planning or multiple operations
3. **User explicitly requests todo list**: When the user directly asks you to track tasks
4. **Multiple tasks**: When users provide a list of things to be done
5. **Dynamic planning**: When the plan may need updates based on intermediate results

## When NOT to Use

Skip this tool when:
1. The task is straightforward and takes less than 3 steps
2. The task is trivial and tracking provides no benefit
3. The task is purely conversational or informational
4. It's clear what needs to be done and you can just do it

## How to Use

1. **Starting a task**: Mark it as `in_progress` BEFORE beginning work
2. **Completing a task**: Mark it as `completed` IMMEDIATELY after finishing
3. **Updating the list**: Add new tasks, remove irrelevant ones, or update descriptions as needed
4. **Multiple updates**: You can make several updates at once (e.g., complete one task and start the next)

## Task States

- `pending`: Task not yet started
- `in_progress`: Currently working on (can have multiple if tasks run in parallel)
- `completed`: Task finished successfully

## Task Completion Requirements

**CRITICAL: Only mark a task as completed when you have FULLY accomplished it.**

Never mark a task as completed if:
- There are unresolved issues or errors
- Work is partial or incomplete
- You encountered blockers preventing completion
- You couldn't find necessary resources or dependencies
- Quality standards haven't been met

If blocked, keep the task as `in_progress` and create a new task describing what needs to be resolved.

## Best Practices

- Create specific, actionable items
- Break complex tasks into smaller, manageable steps
- Use clear, descriptive task names
- Update task status in real-time as you work
- Mark tasks complete IMMEDIATELY after finishing (don't batch completions)
- Remove tasks that are no longer relevant
- **IMPORTANT**: When you write the todo list, mark your first task(s) as `in_progress` immediately
- **IMPORTANT**: Unless all tasks are completed, always have at least one task `in_progress` to show progress

Being proactive with task management demonstrates thoroughness and ensures all requirements are completed successfully.

**Remember**: If you only need a few tool calls to complete a task and it's clear what to do, it's better to just do the task directly and NOT use this tool at all.
"""

    return TodoMiddleware(system_prompt=system_prompt, tool_description=tool_description)


# ---------------------------------------------------------------------------
# Governance middleware factories (Permission, Hook, Compaction)
# ---------------------------------------------------------------------------


def _create_guardrail_middleware() -> AgentMiddleware | None:
    """Create GuardrailMiddleware from config. Returns None if not configured."""
    from deerflow.config.guardrails_config import get_guardrails_config

    guardrails_config = get_guardrails_config()
    if not guardrails_config.enabled or not guardrails_config.provider:
        return None

    import inspect

    from deerflow.guardrails.middleware import GuardrailMiddleware
    from deerflow.reflection import resolve_variable

    provider_cls = resolve_variable(guardrails_config.provider.use)
    provider_kwargs = dict(guardrails_config.provider.config) if guardrails_config.provider.config else {}
    if "framework" not in provider_kwargs:
        try:
            sig = inspect.signature(provider_cls.__init__)
            if "framework" in sig.parameters or any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
                provider_kwargs["framework"] = "deerflow"
        except (ValueError, TypeError):
            pass
    provider = provider_cls(**provider_kwargs)
    return GuardrailMiddleware(
        provider,
        fail_closed=guardrails_config.fail_closed,
        passport=guardrails_config.passport,
    )


def _create_permission_middleware() -> AgentMiddleware | None:
    """Create PermissionMiddleware from config. Returns None if not needed."""
    try:
        from deerflow.config.permissions_config import get_permissions_config

        cfg = get_permissions_config()
        if not cfg.enabled:
            return None

        from deerflow.permissions.middleware import PermissionMiddleware
        from deerflow.permissions.mode import PermissionMode
        from deerflow.permissions.policy import PermissionPolicy

        mode_map = {
            "allow": PermissionMode.ALLOW,
            "prompt": PermissionMode.PROMPT,
            "danger_full_access": PermissionMode.DANGER_FULL_ACCESS,
            "workspace_write": PermissionMode.WORKSPACE_WRITE,
            "read_only": PermissionMode.READ_ONLY,
        }
        active = mode_map.get(cfg.mode, PermissionMode.ALLOW)
        if active == PermissionMode.ALLOW and not cfg.tool_overrides:
            return None

        policy = PermissionPolicy(active_mode=active)
        for tool_name, mode_str in cfg.tool_overrides.items():
            mode = mode_map.get(mode_str, PermissionMode.DANGER_FULL_ACCESS)
            policy = policy.with_tool_requirement(tool_name, mode)

        logger.info("PermissionMiddleware enabled: mode=%s, overrides=%d", active.name, len(cfg.tool_overrides))
        return PermissionMiddleware(policy)
    except Exception:
        logger.debug("PermissionMiddleware not available; skipping", exc_info=True)
        return None


def _create_hook_middleware() -> AgentMiddleware | None:
    """Create HookMiddleware from config. Returns None if no hooks configured."""
    try:
        from deerflow.config.hooks_config import get_hooks_config

        cfg = get_hooks_config()
        if not cfg.enabled:
            return None

        from deerflow.hooks.middleware import HookMiddleware
        from deerflow.hooks.runner import HookRunner

        raw: dict = {}
        if cfg.pre_tool_use:
            raw["pre_tool_use"] = [h.model_dump(exclude_none=True) for h in cfg.pre_tool_use]
        if cfg.post_tool_use:
            raw["post_tool_use"] = [h.model_dump(exclude_none=True) for h in cfg.post_tool_use]
        if cfg.post_tool_use_failure:
            raw["post_tool_use_failure"] = [h.model_dump(exclude_none=True) for h in cfg.post_tool_use_failure]

        if not raw:
            return None

        runner = HookRunner.from_config(raw)
        hook_count = sum(len(v) for v in raw.values())
        logger.info("HookMiddleware enabled: %d hook(s)", hook_count)
        return HookMiddleware(runner)
    except Exception:
        logger.debug("HookMiddleware not available; skipping", exc_info=True)
        return None


def _create_compaction_middleware() -> AgentMiddleware | None:
    """Create CompactionMiddleware for context compression."""
    try:
        from deerflow.context.middleware import CompactionMiddleware

        return CompactionMiddleware()
    except Exception:
        logger.debug("CompactionMiddleware not available; skipping", exc_info=True)
        return None


def _build_middlewares(
    config: RunnableConfig,
    model_name: str | None,
    agent_name: str | None = None,
    custom_middlewares: list[AgentMiddleware] | None = None,
    *,
    app_config: AppConfig | None = None,
):
    """Build middleware chain based on runtime configuration.

    Args:
        config: Runtime configuration containing configurable options like is_plan_mode.
        agent_name: If provided, MemoryMiddleware will use per-agent memory storage.
        custom_middlewares: Optional list of custom middlewares to inject into the chain.

    Returns:
        List of middleware instances.
    """
    resolved_app_config = app_config or get_app_config()
    cfg = _get_runtime_config(config)
    agent_variant = cfg.get("agent_variant") or cfg.get("sandbox_provider_variant")

    summarization_middleware = _call_with_optional_app_config(_create_summarization_middleware, app_config=resolved_app_config)

    # Add ViewImageMiddleware only if the current model supports vision.
    # Use the resolved runtime model_name from the graph factory to avoid stale config values.
    model_config = resolved_app_config.get_model_config(model_name) if model_name else None
    vision_middleware = ViewImageMiddleware() if model_config is not None and model_config.supports_vision else None

    deferred_tool_filter = None
    if resolved_app_config.tool_search.enabled:
        from deerflow.agents.middlewares.deferred_tool_filter_middleware import DeferredToolFilterMiddleware

        deferred_tool_filter = DeferredToolFilterMiddleware()

    subagent_enabled = cfg.get("subagent_enabled", False)
    subagent_limit_middleware = None
    if subagent_enabled:
        max_concurrent_subagents = cfg.get("max_concurrent_subagents", 3)
        subagent_limit_middleware = SubagentLimitMiddleware(max_concurrent=max_concurrent_subagents)

    loop_detection_config = resolved_app_config.loop_detection
    loop_detection_middleware = None
    if loop_detection_config.enabled:
        loop_detection_middleware = LoopDetectionMiddleware.from_config(loop_detection_config)

    safety_config = resolved_app_config.safety_finish_reason
    safety_finish_reason_middleware = None
    if safety_config.enabled:
        safety_finish_reason_middleware = SafetyFinishReasonMiddleware.from_config(safety_config)

    from langchain_dev_utils.agents.middleware import FormatPromptMiddleware

    return build_ordered_middleware_chain(
        sandbox=[
            ThreadDataMiddleware(lazy_init=True),
            UploadsMiddleware(),
            SandboxMiddleware(lazy_init=True, provider_variant=agent_variant),
        ],
        dangling_tool_call_patch=[DanglingToolCallMiddleware()],
        llm_error_handling=[LLMErrorHandlingMiddleware()],
        guardrail=_create_guardrail_middleware(),
        sandbox_audit=[SandboxAuditMiddleware()],
        tool_error_handling=[ToolErrorHandlingMiddleware()],
        permissions=_create_permission_middleware(),
        hooks=_create_hook_middleware(),
        dynamic_context=[DynamicContextMiddleware(agent_name=agent_name)],
        summarization=summarization_middleware,
        compaction=_create_compaction_middleware(),
        plan_mode=_create_todo_list_middleware(cfg.get("is_plan_mode", False)),
        prompt_format=[FormatPromptMiddleware(template_format="jinja2")],
        token_usage=[TokenUsageMiddleware()] if resolved_app_config.token_usage.enabled else None,
        title=[TitleMiddleware(app_config=resolved_app_config)],
        memory=[MemoryMiddleware(agent_name=agent_name, memory_config=resolved_app_config.memory)],
        vision=vision_middleware,
        deferred_tool_filter=deferred_tool_filter,
        subagent_limit=subagent_limit_middleware,
        loop_detection=loop_detection_middleware,
        custom_middlewares=custom_middlewares,
        safety_finish_reason=safety_finish_reason_middleware,
        clarification=[ClarificationMiddleware()],
    )


def _available_skill_names(agent_config, is_bootstrap: bool) -> set[str] | None:
    if is_bootstrap:
        return {"bootstrap"}
    if agent_config and agent_config.skills is not None:
        return set(agent_config.skills)
    return None


def _load_enabled_skills_for_tool_policy(available_skills: set[str] | None, *, app_config: AppConfig) -> list[Skill]:
    try:
        from deerflow.agents.lead_agent.prompt import get_enabled_skills_for_config

        skills = get_enabled_skills_for_config(app_config)
    except Exception:
        logger.exception("Failed to load skills for allowed-tools policy")
        raise

    if available_skills is None:
        return skills
    return [skill for skill in skills if skill.name in available_skills]


def _resolve_effective_tool_groups(agent_config, variant: str) -> list[str] | None:
    defaults = VARIANT_DEFAULTS[variant]
    groups = agent_config.tool_groups if agent_config and agent_config.tool_groups is not None else defaults["tool_groups"]
    if variant != "chat":
        return groups
    source_groups = groups if groups is not None else CHAT_TOOL_GROUPS
    return [group for group in source_groups if group != "bash"]


def _write_effective_runtime_context(
    config: RunnableConfig,
    *,
    variant: str,
    is_plan_mode: bool,
    subagent_enabled: bool,
    max_concurrent_subagents: int,
    sandbox_provider_variant: str,
) -> None:
    context = config.setdefault("context", {})
    if not isinstance(context, dict):
        context = {}
        config["context"] = context
    context.update(
        {
            "agent_variant": variant,
            "sandbox_provider_variant": sandbox_provider_variant,
            "is_plan_mode": is_plan_mode,
            "subagent_enabled": subagent_enabled,
            "max_concurrent_subagents": max_concurrent_subagents,
        }
    )


def _make_variant_lead_agent(config: RunnableConfig, *, variant: str):
    # Lazy import to avoid circular dependency
    from deerflow.tools import get_available_tools
    from deerflow.tools.builtins import setup_agent, update_agent

    if variant not in VARIANT_DEFAULTS:
        raise ValueError(f"Unknown lead agent variant: {variant}")

    cfg = _get_runtime_config(config)
    runtime_app_config = cfg.get("app_config")
    has_runtime_app_config = runtime_app_config is not None
    app_config = runtime_app_config or get_app_config()
    app_config_for_child_calls = app_config if has_runtime_app_config else None

    thinking_enabled = cfg.get("thinking_enabled", True)
    reasoning_effort = cfg.get("reasoning_effort", None)
    requested_model_name: str | None = cfg.get("model_name") or cfg.get("model")
    is_bootstrap = cfg.get("is_bootstrap", False)
    agent_name = validate_agent_name(cfg.get("agent_name"))
    user_id = config.get("metadata", {}).get("user_id")

    if is_bootstrap:
        agent_config = None
    elif user_id is None:
        agent_config = load_agent_config(agent_name)
    else:
        agent_config = load_agent_config(agent_name, user_id=user_id)

    effective_variant = "computer" if is_bootstrap else variant
    if not is_bootstrap and agent_config is not None and getattr(agent_config, "variant", None):
        effective_variant = agent_config.variant
    defaults = VARIANT_DEFAULTS[effective_variant]
    is_plan_mode = cfg.get("is_plan_mode", defaults["is_plan_mode"])
    subagent_enabled = cfg.get("subagent_enabled", defaults["subagent_enabled"])
    max_concurrent_subagents = cfg.get("max_concurrent_subagents", defaults["max_concurrent_subagents"])
    sandbox_provider_variant = defaults["sandbox_provider_variant"]
    tool_groups = _resolve_effective_tool_groups(agent_config, effective_variant)
    _write_effective_runtime_context(
        config,
        variant=effective_variant,
        is_plan_mode=is_plan_mode,
        subagent_enabled=subagent_enabled,
        max_concurrent_subagents=max_concurrent_subagents,
        sandbox_provider_variant=sandbox_provider_variant,
    )

    available_skills = _available_skill_names(agent_config, is_bootstrap)
    # Custom agent model from agent config (if any), or None to let _resolve_model_name pick the default
    agent_model_name = agent_config.model if agent_config and agent_config.model else None

    # Final model name resolution: request → agent config → global default, with fallback for unknown names
    model_name = _call_with_optional_app_config(_resolve_model_name, requested_model_name or agent_model_name, app_config=app_config)
    model_config = app_config.get_model_config(model_name)

    if model_config is None:
        raise ValueError("No chat model could be resolved. Please configure at least one model in config.yaml or provide a valid 'model_name'/'model' in the request.")
    if thinking_enabled and not model_config.supports_thinking:
        logger.warning(f"Thinking mode is enabled but model '{model_name}' does not support it; fallback to non-thinking mode.")
        thinking_enabled = False

    logger.info(
        "Create Agent(%s, variant=%s) -> thinking_enabled: %s, reasoning_effort: %s, model_name: %s, is_plan_mode: %s, subagent_enabled: %s, max_concurrent_subagents: %s",
        agent_name or "default",
        effective_variant,
        thinking_enabled,
        reasoning_effort,
        model_name,
        is_plan_mode,
        subagent_enabled,
        max_concurrent_subagents,
    )

    # Inject run metadata for LangSmith trace tagging
    if "metadata" not in config:
        config["metadata"] = {}
    callbacks = build_tracing_callbacks()
    if callbacks:
        config["callbacks"] = [*list(config.get("callbacks", []) or []), *callbacks]

    config["metadata"].update(
        {
            "agent_name": agent_name or "default",
            "model_name": model_name or "default",
            "thinking_enabled": thinking_enabled,
            "reasoning_effort": reasoning_effort,
            "is_plan_mode": is_plan_mode,
            "subagent_enabled": subagent_enabled,
            "agent_variant": effective_variant,
            "sandbox_provider_variant": sandbox_provider_variant,
            "tool_groups": tool_groups,
            "available_skills": sorted(available_skills) if available_skills is not None else None,
        }
    )

    skills_for_tool_policy = _load_enabled_skills_for_tool_policy(available_skills, app_config=app_config)

    if is_bootstrap:
        # Special bootstrap agent with minimal prompt for initial custom agent creation flow
        available_tools_kwargs = {"model_name": model_name, "groups": tool_groups, "subagent_enabled": subagent_enabled}
        if has_runtime_app_config:
            available_tools_kwargs["app_config"] = app_config
        tools = get_available_tools(**available_tools_kwargs) + [setup_agent]
        return create_agent(
            model=_call_with_optional_app_config(create_chat_model, name=model_name, thinking_enabled=thinking_enabled, attach_tracing=False, app_config=app_config_for_child_calls),
            tools=filter_tools_by_skill_allowed_tools(tools, skills_for_tool_policy),
            middleware=_call_with_optional_app_config(_build_middlewares, config, model_name=model_name, app_config=app_config_for_child_calls),
            system_prompt=apply_prompt_template(
                subagent_enabled=subagent_enabled,
                max_concurrent_subagents=max_concurrent_subagents,
                agent_key=defaults["agent_key"],
                user_id=user_id,
                available_skills=set(["bootstrap"]),
                app_config=app_config_for_child_calls,
            ),
            state_schema=ThreadState,
        )

    # Default lead agent
    available_tools_kwargs = {
        "model_name": model_name,
        "groups": tool_groups,
        "subagent_enabled": subagent_enabled,
    }
    if has_runtime_app_config:
        available_tools_kwargs["app_config"] = app_config
    tools = get_available_tools(**available_tools_kwargs)
    if agent_name:
        tools = tools + [update_agent]
    return create_agent(
        model=_call_with_optional_app_config(create_chat_model, name=model_name, thinking_enabled=thinking_enabled, reasoning_effort=reasoning_effort, attach_tracing=False, app_config=app_config_for_child_calls),
        tools=filter_tools_by_skill_allowed_tools(tools, skills_for_tool_policy),
        middleware=_call_with_optional_app_config(_build_middlewares, config, model_name=model_name, agent_name=agent_name, app_config=app_config_for_child_calls),
        system_prompt=apply_prompt_template(
            subagent_enabled=subagent_enabled,
            max_concurrent_subagents=max_concurrent_subagents,
            agent_key=defaults["agent_key"],
            agent_name=agent_name,
            user_id=user_id,
            available_skills=available_skills,
            app_config=app_config_for_child_calls,
        ),
        state_schema=ThreadState,
    )


def make_chat_lead_agent(config: RunnableConfig):
    return _make_variant_lead_agent(config, variant="chat")


def make_computer_lead_agent(config: RunnableConfig):
    return _make_variant_lead_agent(config, variant="computer")
