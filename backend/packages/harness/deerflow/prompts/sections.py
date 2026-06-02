"""Individual prompt sections — each returns a string or empty string.

Sections are divided into two groups:
  - Static: stable across turns, safe to cache at the LLM API level.
  - Dynamic: vary per session / turn (environment, memory, skills, etc.).

The boundary between them is marked by SYSTEM_PROMPT_DYNAMIC_BOUNDARY.

Section *prose* lives in ``templates/partials/*.j2`` (single source of truth);
the functions here are thin wrappers that supply context and render the
matching partial via :func:`deerflow.prompts.render.render_partial`. This keeps
all human-facing prompt text in Jinja2 rather than inline Python strings.
"""

from datetime import datetime
from typing import Literal

from deerflow.prompts.render import render_partial

DEFAULT_AGENT_NAME = "科学风滚草"
PLATFORM_DEVELOPER = "良渚实验室"
SYSTEM_PROMPT_DYNAMIC_BOUNDARY = "\n<!-- SYSTEM_PROMPT_DYNAMIC_BOUNDARY -->\n"

ToneStyle = Literal["normal", "formal", "concise", "explanatory", "encouraging"]


# ---------------------------------------------------------------------------
# Static sections (cacheable)
# ---------------------------------------------------------------------------


def intro_section(agent_name: str = DEFAULT_AGENT_NAME) -> str:
    return render_partial("intro.j2", agent_name=agent_name)


def platform_persona_section(agent_name: str = DEFAULT_AGENT_NAME) -> str:
    return render_partial("platform_persona.j2", agent_name=agent_name)


def conversation_craft_section() -> str:
    return render_partial("conversation_craft.j2")


def collaboration_mechanics_section() -> str:
    return render_partial("collaboration_mechanics.j2")


def scientific_method_section() -> str:
    """Epistemological discipline for research and high-accuracy tasks."""
    return render_partial("scientific_method.j2")


def system_rules_section() -> str:
    """Runtime reality — pull the model from the language-model hallucination world into the controlled runtime world."""
    return render_partial("system_rules.j2")


def task_philosophy_section() -> str:
    """Behavioral constraints that prevent common agent drift.

    Directly adapted from Claude Code's getSimpleDoingTasksSection().
    """
    return render_partial("task_philosophy.j2")


def actions_section() -> str:
    """Risk-action norms — encode blast-radius thinking into the prompt."""
    return render_partial("risk_actions.j2")


def tool_usage_section() -> str:
    """Correct tool usage grammar — which tool for which job."""
    return render_partial("tool_usage.j2")


def tone_style_section(tone_style: ToneStyle = "normal") -> str:
    """Return a tone-and-style block tailored to the requested tone.

    All variants share base rules; each adjusts verbosity, warmth, and structure.
    """
    return render_partial("tone_style.j2", tone_style=tone_style)


# ---------------------------------------------------------------------------
# Dynamic sections (session-specific)
# ---------------------------------------------------------------------------


def environment_section(
    cwd: str | None = None,
    date_str: str | None = None,
) -> str:
    date_str = date_str or datetime.now().strftime("%Y-%m-%d, %A")
    return render_partial("environment.j2", date_str=date_str, cwd=cwd)


def git_safety_section() -> str:
    """Git Safety Protocol — prevent destructive git operations."""
    return render_partial("git_safety.j2")


def linter_section() -> str:
    """Linter feedback loop — check for errors after editing."""
    return render_partial("linter.j2")


def making_code_changes_section() -> str:
    """Code change discipline — minimal, focused edits."""
    return render_partial("making_code_changes.j2")


def session_guidance_section(
    *,
    subagent_enabled: bool = False,
    has_clarification: bool = True,
    has_verification: bool = False,
    has_explore: bool = False,
    has_plan: bool = False,
) -> str:
    """Feature-gated per-session guidance."""
    return render_partial(
        "session_guidance.j2",
        subagent_enabled=subagent_enabled,
        has_clarification=has_clarification,
        has_verification=has_verification,
        has_explore=has_explore,
        has_plan=has_plan,
    )
