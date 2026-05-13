"""Object-key helpers for the OpenDAL-backed storage layer.

Keeping all key templates in one file means a future rename (e.g. moving
uploads under a tenant prefix) is a single-file change, not a hunt
across the codebase. Every key is normalised to forward-slash form
without a leading slash so both the local-FS and S3 backends treat them
the same way.

Top-level namespaces
--------------------

- ``uploads/{user_id}/{thread_id}/…``   per-thread upload bucket
- ``outputs/{user_id}/{thread_id}/…``   agent-produced artifacts
- ``workspace/{user_id}/{thread_id}/…`` long-lived thread workspace
- ``user-profile/{user_id}/USER.md``    per-user profile document
- ``custom-agents/{user_id}/{name}/…``  user-authored agents
- ``user-extensions/{user_id}/…``       per-user MCP / skill enabling overrides

The ``user_id`` sentinel ``__global__`` keeps "no user in context"
scopes inside the same namespace without needing a separate top-level
prefix; this mirrors the sentinel ``user_memory`` uses for its global
memory row.
"""

from __future__ import annotations

import posixpath
import re

_SAFE_SEGMENT_RE = re.compile(r"^[A-Za-z0-9_.\-]+$")
_ALL_DOTS_RE = re.compile(r"^\.+$")

GLOBAL_SCOPE = "__global__"


def _require_segment(label: str, value: str) -> str:
    if (
        not value
        or not _SAFE_SEGMENT_RE.match(value)
        or _ALL_DOTS_RE.match(value)
        or value.startswith(".")
        or value.endswith(".")
    ):
        raise ValueError(
            f"Invalid {label} {value!r}: must be non-empty, start and end with "
            "an alphanumeric character, and contain only alphanumeric "
            "characters, hyphens, underscores, and interior dots."
        )
    return value


def _user_scope(user_id: str | None) -> str:
    """Return the ``user_id`` segment to use, collapsing None to the global sentinel."""
    if user_id is None:
        return GLOBAL_SCOPE
    return _require_segment("user_id", user_id)


def _normalise_subpath(subpath: str) -> str:
    """Normalise a caller-supplied sub-path within a thread's storage."""
    cleaned = subpath.replace("\\", "/").lstrip("/")
    # ``posixpath.normpath`` collapses ``..`` segments; after that we
    # reject any result that still tries to escape the caller's root.
    normalised = posixpath.normpath(cleaned)
    if normalised.startswith("..") or "/../" in normalised or normalised in ("", "."):
        raise ValueError(f"Invalid subpath: {subpath!r}")
    return normalised


def uploads_prefix(user_id: str, thread_id: str) -> str:
    """Prefix for the upload bucket of a specific thread."""
    return f"uploads/{_require_segment('user_id', user_id)}/{_require_segment('thread_id', thread_id)}"


def uploads_key(user_id: str, thread_id: str, filename: str) -> str:
    """Object key for a single uploaded file."""
    return f"{uploads_prefix(user_id, thread_id)}/{_normalise_subpath(filename)}"


def outputs_prefix(user_id: str, thread_id: str) -> str:
    """Prefix for the agent output bucket of a thread."""
    return f"outputs/{_require_segment('user_id', user_id)}/{_require_segment('thread_id', thread_id)}"


def outputs_key(user_id: str, thread_id: str, subpath: str) -> str:
    """Object key for a single artifact inside a thread's outputs."""
    return f"{outputs_prefix(user_id, thread_id)}/{_normalise_subpath(subpath)}"


def workspace_prefix(user_id: str, thread_id: str) -> str:
    """Prefix for the long-lived workspace of a thread (code & intermediate data)."""
    return f"workspace/{_require_segment('user_id', user_id)}/{_require_segment('thread_id', thread_id)}"


def workspace_key(user_id: str, thread_id: str, subpath: str) -> str:
    """Object key for a single file inside a thread's workspace."""
    return f"{workspace_prefix(user_id, thread_id)}/{_normalise_subpath(subpath)}"


# ---------------------------------------------------------------------------
# Round 2.1 additions: user-editable small configs (USER.md, custom agents,
# per-user extensions override).
# ---------------------------------------------------------------------------


def user_profile_key(user_id: str | None = None) -> str:
    """Object key for ``USER.md`` — the per-user profile document.

    ``user_id=None`` maps to the global scope so the same function covers
    the legacy ``{base_dir}/USER.md`` path.
    """
    return f"user-profile/{_user_scope(user_id)}/USER.md"


def user_agents_prefix(user_id: str | None = None) -> str:
    """Prefix under which all of a user's custom agents live."""
    return f"custom-agents/{_user_scope(user_id)}"


def user_agent_prefix(user_id: str | None, agent_name: str) -> str:
    """Prefix for a single custom agent directory."""
    return f"{user_agents_prefix(user_id)}/{_require_segment('agent_name', agent_name)}"


def user_agent_config_key(user_id: str | None, agent_name: str) -> str:
    """Object key for ``config.yaml`` inside a custom agent."""
    return f"{user_agent_prefix(user_id, agent_name)}/config.yaml"


def user_agent_soul_key(user_id: str | None, agent_name: str) -> str:
    """Object key for the optional ``SOUL.md`` inside a custom agent."""
    return f"{user_agent_prefix(user_id, agent_name)}/SOUL.md"


def user_extensions_override_key(user_id: str) -> str:
    """Object key for the per-user ``extensions_config.json`` override.

    Note this is **not** the repo-level public MCP config; that file stays
    on disk at ``<repo>/extensions_config.json`` and is never addressed
    through the object store.
    """
    return f"user-extensions/{_require_segment('user_id', user_id)}/extensions_config.json"
