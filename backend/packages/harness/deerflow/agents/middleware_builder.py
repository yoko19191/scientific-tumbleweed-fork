"""Canonical middleware builder — single source of truth for chain assembly.

The config-driven LangGraph factories and ``create_deerflow_agent`` (SDK-driven)
delegate to this builder so the middleware order is consistent.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from langchain.agents.middleware import AgentMiddleware

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


MiddlewareSlot = AgentMiddleware | Sequence[AgentMiddleware] | None


def _slot_items(slot: MiddlewareSlot) -> list[AgentMiddleware]:
    if slot is None:
        return []
    if isinstance(slot, AgentMiddleware):
        return [slot]
    return list(slot)


def build_ordered_middleware_chain(
    *,
    sandbox: MiddlewareSlot = None,
    dangling_tool_call_patch: MiddlewareSlot = None,
    llm_error_handling: MiddlewareSlot = None,
    guardrail: MiddlewareSlot = None,
    sandbox_audit: MiddlewareSlot = None,
    tool_error_handling: MiddlewareSlot = None,
    permissions: MiddlewareSlot = None,
    hooks: MiddlewareSlot = None,
    dynamic_context: MiddlewareSlot = None,
    summarization: MiddlewareSlot = None,
    compaction: MiddlewareSlot = None,
    plan_mode: MiddlewareSlot = None,
    prompt_format: MiddlewareSlot = None,
    token_usage: MiddlewareSlot = None,
    title: MiddlewareSlot = None,
    memory: MiddlewareSlot = None,
    vision: MiddlewareSlot = None,
    deferred_tool_filter: MiddlewareSlot = None,
    subagent_limit: MiddlewareSlot = None,
    loop_detection: MiddlewareSlot = None,
    custom_middlewares: MiddlewareSlot = None,
    safety_finish_reason: MiddlewareSlot = None,
    clarification: MiddlewareSlot = None,
) -> list[AgentMiddleware]:
    """Build the canonical middleware order from concrete slot contents."""
    chain: list[AgentMiddleware] = []
    for slot in (
        sandbox,
        dangling_tool_call_patch,
        llm_error_handling,
        guardrail,
        sandbox_audit,
        tool_error_handling,
        permissions,
        hooks,
        dynamic_context,
        summarization,
        compaction,
        plan_mode,
        prompt_format,
        token_usage,
        title,
        memory,
        vision,
        deferred_tool_filter,
        subagent_limit,
        loop_detection,
        custom_middlewares,
        safety_finish_reason,
        clarification,
    ):
        chain.extend(_slot_items(slot))
    ensure_clarification_last(chain)
    return chain


def ensure_clarification_last(chain: list[AgentMiddleware]) -> None:
    """Keep ClarificationMiddleware at the tail when present."""
    from deerflow.agents.middlewares.clarification_middleware import ClarificationMiddleware

    for idx, middleware in enumerate(chain):
        if isinstance(middleware, ClarificationMiddleware):
            if idx != len(chain) - 1:
                chain.append(chain.pop(idx))
            return


def insert_extra_middlewares(chain: list[AgentMiddleware], extras: list[AgentMiddleware]) -> None:
    """Insert extra middlewares via @Next/@Prev anchors, preserving tail invariants."""
    from deerflow.agents.middlewares.clarification_middleware import ClarificationMiddleware

    next_targets: dict[type, type] = {}
    prev_targets: dict[type, type] = {}

    anchored: list[tuple[AgentMiddleware, str, type]] = []
    unanchored: list[AgentMiddleware] = []

    for mw in extras:
        next_anchor = getattr(type(mw), "_next_anchor", None)
        prev_anchor = getattr(type(mw), "_prev_anchor", None)

        if next_anchor and prev_anchor:
            raise ValueError(f"{type(mw).__name__} cannot have both @Next and @Prev")

        if next_anchor:
            if next_anchor in next_targets:
                raise ValueError(
                    f"Conflict: {type(mw).__name__} and "
                    f"{next_targets[next_anchor].__name__} both @Next({next_anchor.__name__})"
                )
            if next_anchor in prev_targets:
                raise ValueError(
                    f"Conflict: {type(mw).__name__} @Next({next_anchor.__name__}) and "
                    f"{prev_targets[next_anchor].__name__} @Prev({next_anchor.__name__}) "
                    "- use cross-anchoring between extras instead"
                )
            next_targets[next_anchor] = type(mw)
            anchored.append((mw, "next", next_anchor))
        elif prev_anchor:
            if prev_anchor in prev_targets:
                raise ValueError(
                    f"Conflict: {type(mw).__name__} and "
                    f"{prev_targets[prev_anchor].__name__} both @Prev({prev_anchor.__name__})"
                )
            if prev_anchor in next_targets:
                raise ValueError(
                    f"Conflict: {type(mw).__name__} @Prev({prev_anchor.__name__}) and "
                    f"{next_targets[prev_anchor].__name__} @Next({prev_anchor.__name__}) "
                    "- use cross-anchoring between extras instead"
                )
            prev_targets[prev_anchor] = type(mw)
            anchored.append((mw, "prev", prev_anchor))
        else:
            unanchored.append(mw)

    clarification_idx = next(i for i, m in enumerate(chain) if isinstance(m, ClarificationMiddleware))
    for mw in unanchored:
        chain.insert(clarification_idx, mw)
        clarification_idx += 1

    pending = list(anchored)
    max_rounds = len(pending) + 1
    for _ in range(max_rounds):
        if not pending:
            break
        remaining = []
        for mw, direction, anchor in pending:
            try:
                idx = next(i for i, m in enumerate(chain) if isinstance(m, anchor))
            except StopIteration:
                remaining.append((mw, direction, anchor))
                continue
            insert_at = idx + 1 if direction == "next" else idx
            chain.insert(insert_at, mw)
        if len(remaining) == len(pending):
            names = [f"{type(mw).__name__} @{direction}({anchor.__name__})" for mw, direction, anchor in remaining]
            if any(getattr(type(mw), "_next_anchor", None) in {type(x) for x, _, _ in remaining} for mw, _, _ in remaining):
                raise ValueError(f"Circular dependency among extra_middleware: {names}")
            raise ValueError(f"Cannot resolve middleware anchors: {names}")
        pending = remaining

    ensure_clarification_last(chain)


@dataclass
class MiddlewareFeatures:
    """Feature flags controlling which middlewares are included."""

    sandbox: bool = True
    uploads: bool = True
    dangling_tool_call_patch: bool = True
    permissions: bool = True
    guardrail: bool = True
    hooks: bool = True
    sandbox_audit: bool = True
    tool_error_handling: bool = True
    dynamic_context: bool = True
    summarization: bool = False
    compaction: bool = False
    plan_mode: bool = False
    token_usage: bool = False
    title: bool = True
    memory: bool = True
    vision: bool = False
    deferred_tool_filter: bool = False
    subagent_limit: bool = False
    loop_detection: bool = True
    safety_finish_reason: bool = True
    clarification: bool = True

    lazy_init: bool = True
    agent_name: str | None = None
    model_name: str | None = None
    max_concurrent_subagents: int = 3

    custom_middlewares: list[AgentMiddleware] = field(default_factory=list)


def build_canonical_middleware_chain(features: MiddlewareFeatures) -> list[AgentMiddleware]:
    """Assemble concrete middleware slots and delegate canonical ordering."""
    sandbox: list[AgentMiddleware] = []
    dangling_tool_call_patch: list[AgentMiddleware] = []
    llm_error_handling: list[AgentMiddleware] = []
    permissions: list[AgentMiddleware] = []
    guardrail: list[AgentMiddleware] = []
    hooks: list[AgentMiddleware] = []
    sandbox_audit: list[AgentMiddleware] = []
    tool_error_handling: list[AgentMiddleware] = []
    dynamic_context: list[AgentMiddleware] = []
    summarization: list[AgentMiddleware] = []
    compaction: list[AgentMiddleware] = []
    plan_mode: list[AgentMiddleware] = []
    token_usage: list[AgentMiddleware] = []
    title: list[AgentMiddleware] = []
    memory: list[AgentMiddleware] = []
    vision: list[AgentMiddleware] = []
    deferred_tool_filter: list[AgentMiddleware] = []
    subagent_limit: list[AgentMiddleware] = []
    loop_detection: list[AgentMiddleware] = []
    safety_finish_reason: list[AgentMiddleware] = []
    clarification: list[AgentMiddleware] = []

    if features.sandbox:
        from deerflow.agents.middlewares.thread_data_middleware import ThreadDataMiddleware
        from deerflow.sandbox.middleware import SandboxMiddleware

        sandbox.append(ThreadDataMiddleware(lazy_init=features.lazy_init))

        if features.uploads:
            from deerflow.agents.middlewares.uploads_middleware import UploadsMiddleware

            sandbox.append(UploadsMiddleware())

        sandbox.append(SandboxMiddleware(lazy_init=features.lazy_init))

    if features.dangling_tool_call_patch:
        from deerflow.agents.middlewares.dangling_tool_call_middleware import DanglingToolCallMiddleware

        dangling_tool_call_patch.append(DanglingToolCallMiddleware())

    from deerflow.agents.middlewares.llm_error_handling_middleware import LLMErrorHandlingMiddleware

    llm_error_handling.append(LLMErrorHandlingMiddleware())

    if features.guardrail:
        _maybe_add_guardrail_middleware(guardrail)

    if features.sandbox_audit:
        from deerflow.agents.middlewares.sandbox_audit_middleware import SandboxAuditMiddleware

        sandbox_audit.append(SandboxAuditMiddleware())

    if features.tool_error_handling:
        from deerflow.agents.middlewares.tool_error_handling_middleware import ToolErrorHandlingMiddleware

        tool_error_handling.append(ToolErrorHandlingMiddleware())

    if features.permissions:
        _maybe_add_permission_middleware(permissions)

    if features.hooks:
        _maybe_add_hook_middleware(hooks)

    if features.dynamic_context:
        from deerflow.agents.middlewares.dynamic_context_middleware import DynamicContextMiddleware

        dynamic_context.append(DynamicContextMiddleware(agent_name=features.agent_name))

    if features.summarization:
        _maybe_add_summarization_middleware(summarization)

    if features.compaction:
        _maybe_add_compaction_middleware(compaction)

    if features.plan_mode:
        from deerflow.agents.middlewares.todo_middleware import TodoMiddleware

        plan_mode.append(TodoMiddleware())

    if features.token_usage:
        from deerflow.agents.middlewares.token_usage_middleware import TokenUsageMiddleware

        token_usage.append(TokenUsageMiddleware())

    if features.title:
        from deerflow.agents.middlewares.title_middleware import TitleMiddleware

        title.append(TitleMiddleware())

    if features.memory:
        from deerflow.agents.middlewares.memory_middleware import MemoryMiddleware

        memory.append(MemoryMiddleware(agent_name=features.agent_name))

    if features.vision:
        from deerflow.agents.middlewares.view_image_middleware import ViewImageMiddleware

        vision.append(ViewImageMiddleware())

    if features.deferred_tool_filter:
        from deerflow.agents.middlewares.deferred_tool_filter_middleware import DeferredToolFilterMiddleware

        deferred_tool_filter.append(DeferredToolFilterMiddleware())

    if features.subagent_limit:
        from deerflow.agents.middlewares.subagent_limit_middleware import SubagentLimitMiddleware

        subagent_limit.append(SubagentLimitMiddleware(max_concurrent=features.max_concurrent_subagents))

    if features.loop_detection:
        from deerflow.config.app_config import get_app_config

        loop_detection_config = get_app_config().loop_detection
        if loop_detection_config.enabled:
            from deerflow.agents.middlewares.loop_detection_middleware import LoopDetectionMiddleware

            loop_detection.append(LoopDetectionMiddleware.from_config(loop_detection_config))

    if features.safety_finish_reason:
        from deerflow.config.app_config import get_app_config

        safety_config = get_app_config().safety_finish_reason
        if safety_config.enabled:
            from deerflow.agents.middlewares.safety_finish_reason_middleware import SafetyFinishReasonMiddleware

            safety_finish_reason.append(SafetyFinishReasonMiddleware.from_config(safety_config))

    if features.clarification:
        from deerflow.agents.middlewares.clarification_middleware import ClarificationMiddleware

        clarification.append(ClarificationMiddleware())

    return build_ordered_middleware_chain(
        sandbox=sandbox,
        dangling_tool_call_patch=dangling_tool_call_patch,
        llm_error_handling=llm_error_handling,
        guardrail=guardrail,
        sandbox_audit=sandbox_audit,
        tool_error_handling=tool_error_handling,
        permissions=permissions,
        hooks=hooks,
        dynamic_context=dynamic_context,
        summarization=summarization,
        compaction=compaction,
        plan_mode=plan_mode,
        token_usage=token_usage,
        title=title,
        memory=memory,
        vision=vision,
        deferred_tool_filter=deferred_tool_filter,
        subagent_limit=subagent_limit,
        loop_detection=loop_detection,
        custom_middlewares=features.custom_middlewares,
        safety_finish_reason=safety_finish_reason,
        clarification=clarification,
    )


# ---------------------------------------------------------------------------
# Internal helpers for conditional middleware creation
# ---------------------------------------------------------------------------


def _maybe_add_permission_middleware(chain: list[AgentMiddleware]) -> None:
    """Add PermissionMiddleware if permissions are configured and not in allow-all mode."""
    from deerflow.config.permissions_config import get_permissions_config
    from deerflow.permissions.middleware import PermissionMiddleware
    from deerflow.permissions.mode import PermissionMode
    from deerflow.permissions.policy import PermissionPolicy

    cfg = get_permissions_config()
    if not cfg.enabled:
        return

    mode_map = {
        "allow": PermissionMode.ALLOW,
        "prompt": PermissionMode.PROMPT,
        "danger_full_access": PermissionMode.DANGER_FULL_ACCESS,
        "workspace_write": PermissionMode.WORKSPACE_WRITE,
        "read_only": PermissionMode.READ_ONLY,
    }
    active = mode_map.get(cfg.mode, PermissionMode.ALLOW)

    if active == PermissionMode.ALLOW and not cfg.tool_overrides:
        return

    policy = PermissionPolicy(active_mode=active)
    for tool_name, mode_str in cfg.tool_overrides.items():
        mode = mode_map.get(mode_str, PermissionMode.DANGER_FULL_ACCESS)
        policy = policy.with_tool_requirement(tool_name, mode)

    chain.append(PermissionMiddleware(policy))


def _maybe_add_guardrail_middleware(chain: list[AgentMiddleware]) -> None:
    """Add GuardrailMiddleware if a provider is configured."""
    import inspect

    from deerflow.config.guardrails_config import get_guardrails_config
    from deerflow.guardrails.middleware import GuardrailMiddleware
    from deerflow.reflection import resolve_variable

    cfg = get_guardrails_config()
    if not cfg.enabled or not cfg.provider:
        return

    provider_cls = resolve_variable(cfg.provider.use)
    kwargs = dict(cfg.provider.config) if cfg.provider.config else {}
    if "framework" not in kwargs:
        try:
            sig = inspect.signature(provider_cls.__init__)
            if "framework" in sig.parameters or any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
                kwargs["framework"] = "deerflow"
        except (ValueError, TypeError):
            pass
    provider = provider_cls(**kwargs)
    chain.append(GuardrailMiddleware(provider, fail_closed=cfg.fail_closed, passport=cfg.passport))


def _maybe_add_hook_middleware(chain: list[AgentMiddleware]) -> None:
    """Add HookMiddleware if hooks are configured and enabled."""
    from deerflow.config.hooks_config import get_hooks_config
    from deerflow.hooks.middleware import HookMiddleware
    from deerflow.hooks.runner import HookRunner

    cfg = get_hooks_config()
    if not cfg.enabled:
        return

    raw: dict = {}
    if cfg.pre_tool_use:
        raw["pre_tool_use"] = [h.model_dump(exclude_none=True) for h in cfg.pre_tool_use]
    if cfg.post_tool_use:
        raw["post_tool_use"] = [h.model_dump(exclude_none=True) for h in cfg.post_tool_use]
    if cfg.post_tool_use_failure:
        raw["post_tool_use_failure"] = [h.model_dump(exclude_none=True) for h in cfg.post_tool_use_failure]

    if raw:
        runner = HookRunner.from_config(raw)
        chain.append(HookMiddleware(runner))


def _maybe_add_summarization_middleware(chain: list[AgentMiddleware]) -> None:
    """Add SummarizationMiddleware from config if enabled."""
    from langchain.agents.middleware import SummarizationMiddleware

    from deerflow.config.summarization_config import get_summarization_config
    from deerflow.models import create_chat_model

    cfg = get_summarization_config()
    if not cfg.enabled:
        return

    trigger = None
    if cfg.trigger is not None:
        if isinstance(cfg.trigger, list):
            trigger = [t.to_tuple() for t in cfg.trigger]
        else:
            trigger = cfg.trigger.to_tuple()

    keep = cfg.keep.to_tuple()
    model = create_chat_model(name=cfg.model_name, thinking_enabled=False) if cfg.model_name else create_chat_model(thinking_enabled=False)

    kwargs = {"model": model, "trigger": trigger, "keep": keep}
    if cfg.trim_tokens_to_summarize is not None:
        kwargs["trim_tokens_to_summarize"] = cfg.trim_tokens_to_summarize
    if cfg.summary_prompt is not None:
        kwargs["summary_prompt"] = cfg.summary_prompt

    chain.append(SummarizationMiddleware(**kwargs))


def _maybe_add_compaction_middleware(chain: list[AgentMiddleware]) -> None:
    """Add CompactionMiddleware if context compaction is configured."""
    try:
        from deerflow.context.middleware import CompactionMiddleware

        chain.append(CompactionMiddleware())
    except ImportError:
        logger.debug("CompactionMiddleware not yet available; skipping")
