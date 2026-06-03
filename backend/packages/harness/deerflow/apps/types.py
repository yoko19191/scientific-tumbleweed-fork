"""Types for modular workspace apps."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

AppStatus = Literal["available", "coming_soon"]
AppLaunchMode = Literal["chat", "computer"]


@dataclass(frozen=True)
class AppLaunch:
    """How the frontend should start a registered workspace app."""

    href: str
    mode: AppLaunchMode = "chat"


@dataclass(frozen=True)
class AppDefinition:
    """Metadata for one modular workspace app."""

    id: str
    title: str
    description: str
    category: str
    launch: AppLaunch | None = None
    icon: str = "layout-grid"
    status: AppStatus = "available"
    featured: bool = False
    tags: tuple[str, ...] = field(default_factory=tuple)
    meta: str = ""
