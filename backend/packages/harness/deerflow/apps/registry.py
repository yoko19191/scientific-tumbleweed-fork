"""In-memory registry for workspace app modules."""

from __future__ import annotations

from deerflow.apps.types import AppDefinition

_apps: dict[str, AppDefinition] = {}


def register_app(app: AppDefinition) -> AppDefinition:
    """Register a workspace app module definition.

    Real app modules should call this during their module import. Keeping this
    registry in the harness layer lets Gateway expose app metadata without the
    reusable DeerFlow package depending on ``app.*``.
    """
    if app.id in _apps:
        raise ValueError(f"Workspace app '{app.id}' is already registered")
    _apps[app.id] = app
    return app


def list_apps() -> list[AppDefinition]:
    """Return registered workspace apps sorted by title."""
    return sorted(_apps.values(), key=lambda app: (app.title.lower(), app.id))


def clear_apps() -> None:
    """Clear the app registry.

    This is primarily for focused tests and development reload hooks.
    """
    _apps.clear()
