"""Workspace app registry.

Apps are feature modules that can surface focused workflows in the web UI.
The registry intentionally starts empty; real apps should register their own
``AppDefinition`` from dedicated modules instead of relying on placeholder
catalog data.
"""

from deerflow.apps.registry import clear_apps, list_apps, register_app
from deerflow.apps.types import AppDefinition, AppLaunch

__all__ = [
    "AppDefinition",
    "AppLaunch",
    "clear_apps",
    "list_apps",
    "register_app",
]
