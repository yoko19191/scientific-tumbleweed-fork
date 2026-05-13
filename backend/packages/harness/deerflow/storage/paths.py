"""Object-key helpers for the OpenDAL-backed storage layer.

Keeping all key templates in one file means a future rename (e.g. moving
uploads under a tenant prefix) is a single-file change, not a hunt
across the codebase. Every key is normalised to forward-slash form
without a leading slash so both the local-FS and S3 backends treat them
the same way.
"""

from __future__ import annotations

import posixpath
import re

_SAFE_SEGMENT_RE = re.compile(r"^[A-Za-z0-9_.\-]+$")


def _require_segment(label: str, value: str) -> str:
    if not value or not _SAFE_SEGMENT_RE.match(value):
        raise ValueError(
            f"Invalid {label} {value!r}: must be non-empty and contain only "
            "alphanumeric characters, hyphens, underscores, and dots."
        )
    return value


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
