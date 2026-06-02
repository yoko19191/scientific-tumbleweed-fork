"""Phase 0 golden snapshot tests for the unified ``build_prompt`` factory.

These snapshots are the protective net for the agents-modularization refactor
(see ``docs/refactor/20260602_agents_modularization.md``). They pin the exact
byte output of every lead-agent and subagent prompt produced by
``build_prompt`` *before* the refactor, so any semantic drift introduced while
moving prompt text into Jinja2 partials is caught immediately.

Determinism: every case uses a fixed ``PromptContext`` (fixed ``date_str``, no
ambient skills/memory/soul), so the rendered output depends only on the
templates + ground_truth + section functions — never on environment state.

To regenerate baselines on purpose (after an *intended* change), run:

    UPDATE_PROMPT_SNAPSHOTS=1 PYTHONPATH=. uv run pytest tests/test_prompt_snapshot.py

and review the diff carefully before committing.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from deerflow.prompts.factory import PromptContext, build_prompt
from deerflow.prompts.sections import SYSTEM_PROMPT_DYNAMIC_BOUNDARY

_SNAPSHOT_DIR = Path(__file__).parent / "snapshots"
_FIXED_DATE = "2026-06-02"

# Lead variants are exercised with subagent both off and on so the conditional
# subagent section + session-guidance lines are covered by the baseline.
_LEAD_CASES: dict[str, PromptContext] = {
    "chat_lead__subagent_off": PromptContext(
        variant="chat",
        date_str=_FIXED_DATE,
        subagent_enabled=False,
    ),
    "chat_lead__subagent_on": PromptContext(
        variant="chat",
        date_str=_FIXED_DATE,
        subagent_enabled=True,
        subagent_section="<subagent_system>SNAPSHOT_SUBAGENT_PLACEHOLDER</subagent_system>",
        has_verification=True,
        has_explore=True,
        has_plan=True,
    ),
    "computer_lead__subagent_off": PromptContext(
        variant="computer",
        date_str=_FIXED_DATE,
        subagent_enabled=False,
    ),
    "computer_lead__subagent_on": PromptContext(
        variant="computer",
        date_str=_FIXED_DATE,
        subagent_enabled=True,
        subagent_section="<subagent_system>SNAPSHOT_SUBAGENT_PLACEHOLDER</subagent_system>",
        has_verification=True,
        has_explore=True,
        has_plan=True,
    ),
}

_LEAD_KEYS = {
    "chat_lead__subagent_off": "chat_lead",
    "chat_lead__subagent_on": "chat_lead",
    "computer_lead__subagent_off": "computer_lead",
    "computer_lead__subagent_on": "computer_lead",
}

_SUBAGENT_KEYS = ["general-purpose", "bash", "explore", "plan", "verification"]


def _subagent_ctx() -> PromptContext:
    return PromptContext(date_str=_FIXED_DATE)


def _assert_snapshot(name: str, rendered: str) -> None:
    """Compare ``rendered`` against the stored golden file (or write it)."""
    _SNAPSHOT_DIR.mkdir(exist_ok=True)
    path = _SNAPSHOT_DIR / f"{name}.txt"

    if os.environ.get("UPDATE_PROMPT_SNAPSHOTS") or not path.exists():
        path.write_text(rendered, encoding="utf-8")
        if os.environ.get("UPDATE_PROMPT_SNAPSHOTS"):
            return  # explicit regeneration: don't also assert this run
        # First-ever generation: nothing to compare against yet.
        pytest.skip(f"Wrote new snapshot baseline: {path.name}")

    expected = path.read_text(encoding="utf-8")
    assert rendered == expected, f"Prompt snapshot drift for {name!r}. If this change is intentional, regenerate with UPDATE_PROMPT_SNAPSHOTS=1 and review the diff."


# ---------------------------------------------------------------------------
# Golden snapshots
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("case_name", list(_LEAD_CASES))
def test_lead_prompt_snapshot(case_name: str) -> None:
    rendered = build_prompt(_LEAD_KEYS[case_name], _LEAD_CASES[case_name])
    _assert_snapshot(case_name, rendered)


@pytest.mark.parametrize("agent_key", _SUBAGENT_KEYS)
def test_subagent_prompt_snapshot(agent_key: str) -> None:
    rendered = build_prompt(agent_key, _subagent_ctx())
    _assert_snapshot(f"subagent__{agent_key}", rendered)


# ---------------------------------------------------------------------------
# Structural contracts (independent of exact bytes)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("case_name", list(_LEAD_CASES))
def test_lead_prompt_has_single_cache_boundary(case_name: str) -> None:
    rendered = build_prompt(_LEAD_KEYS[case_name], _LEAD_CASES[case_name])
    assert rendered.count(SYSTEM_PROMPT_DYNAMIC_BOUNDARY) == 1


@pytest.mark.parametrize("case_name", list(_LEAD_CASES))
def test_lead_prompt_static_prefix_contract(case_name: str) -> None:
    rendered = build_prompt(_LEAD_KEYS[case_name], _LEAD_CASES[case_name])
    static_prefix, dynamic_suffix = rendered.split(SYSTEM_PROMPT_DYNAMIC_BOUNDARY, 1)

    # Identity / branding live in the cacheable static prefix.
    for marker in ("<role>", "<platform_persona>", "<scientific_method>", "<git_safety>"):
        assert marker in static_prefix, f"{marker} missing from static prefix in {case_name}"
    assert "科学风滚草" in static_prefix
    assert "良渚实验室" in static_prefix
    # Legacy branding must never resurface.
    assert "DeerFlow 2.0" not in rendered
    # Tone/style is a per-session dynamic section.
    assert "<tone_and_style>" in dynamic_suffix


def test_subagent_prompt_includes_ground_truth() -> None:
    rendered = build_prompt("explore", _subagent_ctx())
    assert "<ground_truth>" in rendered
    assert "科学风滚草" in rendered


def test_subagent_on_injects_subagent_section() -> None:
    rendered = build_prompt("computer_lead", _LEAD_CASES["computer_lead__subagent_on"])
    assert "SNAPSHOT_SUBAGENT_PLACEHOLDER" in rendered


def test_subagent_off_omits_subagent_section() -> None:
    rendered = build_prompt("computer_lead", _LEAD_CASES["computer_lead__subagent_off"])
    assert "SNAPSHOT_SUBAGENT_PLACEHOLDER" not in rendered
