"""Unified Jinja2-backed prompt factory for lead agents and subagents."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader

from deerflow.prompts.sections import (
    DEFAULT_AGENT_NAME,
    SYSTEM_PROMPT_DYNAMIC_BOUNDARY,
    ToneStyle,
    actions_section,
    collaboration_mechanics_section,
    conversation_craft_section,
    environment_section,
    git_safety_section,
    intro_section,
    linter_section,
    making_code_changes_section,
    platform_persona_section,
    scientific_method_section,
    session_guidance_section,
    system_rules_section,
    task_philosophy_section,
    tone_style_section,
    tool_usage_section,
)

_PROMPTS_DIR = Path(__file__).resolve().parents[1]
_TEMPLATES_DIR = _PROMPTS_DIR / "templates"
_GROUND_TRUTH_PATH = _PROMPTS_DIR / "ground_truth.yaml"

_LEAD_AGENT_KEYS = {
    "chat_lead": "lead/chat.j2",
    "computer_lead": "lead/computer.j2",
}
_SUBAGENT_KEYS = {
    "general-purpose": "subagents/general-purpose.j2",
    "bash": "subagents/bash.j2",
    "explore": "subagents/explore.j2",
    "plan": "subagents/plan.j2",
    "verification": "subagents/verification.j2",
}


@dataclass(frozen=True)
class PromptContext:
    """Build-time prompt context shared by lead agents and subagents."""

    variant: str | None = None
    agent_name: str | None = None
    tone_style: ToneStyle = "normal"
    soul: str = ""
    memory: str = ""
    skills_section: str = ""
    deferred_tools_section: str = ""
    subagent_section: str = ""
    subagent_enabled: bool = False
    clarification_section: str = ""
    working_directory_section: str = ""
    citations_section: str = ""
    self_update_section: str = ""
    mcp_instructions: str = ""
    project_rules: str = ""
    cwd: str | None = None
    date_str: str | None = None
    has_verification: bool = False
    has_explore: bool = False
    has_plan: bool = False
    skill_messages: str = ""
    custom_prompt: str = ""


@lru_cache(maxsize=1)
def _load_ground_truth() -> dict[str, Any]:
    with _GROUND_TRUTH_PATH.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError("ground_truth.yaml must contain a mapping")
    return data


@lru_cache(maxsize=1)
def _get_environment() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
        cache_size=64,
    )
    env.globals["ground_truth"] = _load_ground_truth()
    return env


def _coerce_context(ctx: PromptContext | dict[str, Any] | None) -> PromptContext:
    if ctx is None:
        return PromptContext()
    if isinstance(ctx, PromptContext):
        return ctx
    return PromptContext(**ctx)


def _build_lead_static_sections(ctx: PromptContext) -> str:
    name = ctx.agent_name or DEFAULT_AGENT_NAME
    sections = [
        intro_section(name),
        platform_persona_section(name),
        conversation_craft_section(),
        collaboration_mechanics_section(),
        scientific_method_section(),
        system_rules_section(),
        task_philosophy_section(),
        actions_section(),
        git_safety_section(),
        tool_usage_section(),
        making_code_changes_section(),
        linter_section(),
    ]
    return "\n\n".join(s for s in sections if s and s.strip())


def _build_lead_dynamic_sections(ctx: PromptContext) -> str:
    sections: list[str] = []
    for section in (ctx.soul, ctx.memory):
        if section:
            sections.append(section)
    if ctx.cwd or ctx.date_str:
        sections.append(environment_section(ctx.cwd, ctx.date_str))
    sections.append(tone_style_section(ctx.tone_style))
    guidance = session_guidance_section(
        subagent_enabled=ctx.subagent_enabled,
        has_verification=ctx.has_verification,
        has_explore=ctx.has_explore,
        has_plan=ctx.has_plan,
    )
    if guidance:
        sections.append(guidance)
    for section in (
        ctx.skills_section,
        ctx.deferred_tools_section,
        ctx.subagent_section,
        ctx.clarification_section,
        ctx.working_directory_section,
        ctx.citations_section,
        ctx.mcp_instructions,
        ctx.project_rules,
        ctx.self_update_section,
    ):
        if section:
            sections.append(section)
    return "\n\n".join(s for s in sections if s and s.strip())


def build_prompt(agent_key: str, ctx: PromptContext | dict[str, Any] | None = None) -> str:
    """Render a lead-agent or subagent system prompt from the unified factory."""
    prompt_ctx = _coerce_context(ctx)
    env = _get_environment()

    if agent_key in _LEAD_AGENT_KEYS:
        template = env.get_template(_LEAD_AGENT_KEYS[agent_key])
        return template.render(
            static_sections=_build_lead_static_sections(prompt_ctx),
            dynamic_boundary=SYSTEM_PROMPT_DYNAMIC_BOUNDARY,
            dynamic_sections=_build_lead_dynamic_sections(prompt_ctx),
            ctx=prompt_ctx,
        ).strip()

    template_name = _SUBAGENT_KEYS.get(agent_key, "subagents/custom.j2")
    template = env.get_template(template_name)
    return template.render(
        ctx=prompt_ctx,
        custom_prompt=prompt_ctx.custom_prompt,
        skill_messages=prompt_ctx.skill_messages,
    ).strip()
