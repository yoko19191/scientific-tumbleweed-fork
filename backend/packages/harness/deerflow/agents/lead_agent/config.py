"""Typed profiles for lead-agent variants."""

from __future__ import annotations

from dataclasses import dataclass

CHAT_TOOL_GROUPS = ["web", "academic_search", "file:read", "file:write"]


@dataclass(frozen=True)
class LeadProfile:
    """Build-time defaults for a concrete lead-agent variant."""

    variant: str
    agent_key: str
    is_plan_mode: bool
    subagent_enabled: bool
    max_concurrent_subagents: int
    tool_groups: list[str] | None
    sandbox_provider_variant: str


CHAT_PROFILE = LeadProfile(
    variant="chat",
    agent_key="chat_lead",
    is_plan_mode=True,
    subagent_enabled=True,
    max_concurrent_subagents=3,
    tool_groups=CHAT_TOOL_GROUPS,
    sandbox_provider_variant="chat",
)

COMPUTER_PROFILE = LeadProfile(
    variant="computer",
    agent_key="computer_lead",
    is_plan_mode=True,
    subagent_enabled=True,
    max_concurrent_subagents=5,
    tool_groups=None,
    sandbox_provider_variant="computer",
)

_LEAD_PROFILES = {
    CHAT_PROFILE.variant: CHAT_PROFILE,
    COMPUTER_PROFILE.variant: COMPUTER_PROFILE,
}


def get_lead_profile(variant: str) -> LeadProfile:
    try:
        return _LEAD_PROFILES[variant]
    except KeyError as exc:
        raise ValueError(f"Unknown lead agent variant: {variant}") from exc
