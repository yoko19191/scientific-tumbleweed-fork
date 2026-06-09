"""Workspace app registry.

Apps are feature modules that can surface focused workflows in the web UI.
Built-in apps register through explicit loader functions so the harness layer
stays independent from the Gateway application.
"""

from deerflow.apps.registry import clear_apps, list_apps, register_app
from deerflow.apps.research_data_search import register_research_data_search_app
from deerflow.apps.types import AppDefinition, AppLaunch


def load_builtin_apps() -> None:
    """Register workspace apps shipped with the repository."""
    register_research_data_search_app()


load_builtin_apps()

__all__ = [
    "AppDefinition",
    "AppLaunch",
    "clear_apps",
    "load_builtin_apps",
    "list_apps",
    "register_app",
    "register_research_data_search_app",
]
