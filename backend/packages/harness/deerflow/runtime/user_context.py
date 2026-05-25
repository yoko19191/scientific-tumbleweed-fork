"""Request user context helpers for cross-thread execution paths."""

from __future__ import annotations

from contextvars import ContextVar, Token
from typing import Any

DEFAULT_USER_ID = "default"

_current_user: ContextVar[Any | None] = ContextVar("deerflow_current_user", default=None)


def set_current_user(user: Any) -> Token[Any | None]:
    """Set the current request user and return a token for reset."""
    return _current_user.set(user)


def reset_current_user(token: Token[Any | None]) -> None:
    """Reset the current request user context."""
    _current_user.reset(token)


def get_current_user() -> Any | None:
    """Return the current request user object, if one is set."""
    return _current_user.get()


def get_effective_user_id(default: str = DEFAULT_USER_ID) -> str:
    """Return current user id, or a stable default for internal/global paths."""
    user = get_current_user()
    user_id = getattr(user, "id", None) if user is not None else None
    return str(user_id) if user_id is not None else default


def resolve_runtime_user_id(runtime: Any, default: str | None = None) -> str | None:
    """Resolve a user ID from runtime context, falling back to request context."""
    context = getattr(runtime, "context", None)
    if isinstance(context, dict):
        user_id = context.get("user_id")
        if user_id is not None:
            return str(user_id)

    user = get_current_user()
    user_id = getattr(user, "id", None) if user is not None else None
    if user_id is not None:
        return str(user_id)
    return default
