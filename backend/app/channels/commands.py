"""Shared IM channel command registry."""

from __future__ import annotations

KNOWN_CHANNEL_COMMANDS: frozenset[str] = frozenset(
    {
        "bootstrap",
        "help",
        "memory",
        "models",
        "new",
        "status",
    }
)
