"""Canonical user resource prefix helpers.

All per-user Store keys and filesystem resource identifiers must use the
helpers in this module so that the namespace format is defined in one place.

Store key format
----------------
LangGraph Store keys are ``(namespace_tuple, key_string)`` pairs.  For
user-scoped resources the *namespace* already encodes the user, so the key
string is just the resource identifier (e.g. ``thread_id``).  The helpers
below return the namespace tuples that should be used for each resource type.

Filesystem label format
-----------------------
Physical paths are managed by :mod:`deerflow.config.paths` (``Paths``).
The helpers here return the *user_id* string after validation so callers can
pass it directly to ``Paths`` methods.

User ID validation
------------------
User IDs come from JWT ``sub`` claims (UUID strings).  Valid characters are
alphanumeric, hyphens, and underscores.  Empty strings, path separators,
backslashes, and other unsafe characters are rejected.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

_SAFE_USER_ID_RE = re.compile(r"^[A-Za-z0-9_\-]+$")


def validate_user_id(user_id: str) -> str:
    """Validate *user_id* and return it unchanged.

    Raises:
        ValueError: If *user_id* is empty, contains path separators,
                    backslashes, or any character outside ``[A-Za-z0-9_-]``.
    """
    if not user_id:
        raise ValueError("user_id must not be empty")
    if "/" in user_id or "\\" in user_id:
        raise ValueError(f"user_id {user_id!r} must not contain path separators")
    if not _SAFE_USER_ID_RE.match(user_id):
        raise ValueError(
            f"user_id {user_id!r} contains unsafe characters; "
            "only alphanumeric characters, hyphens, and underscores are allowed"
        )
    return user_id


# ---------------------------------------------------------------------------
# Store namespace helpers
# ---------------------------------------------------------------------------

# Base namespace tuples — resource-type namespaces shared across all users.
_THREADS_BASE_NS: tuple[str, ...] = ("threads",)
_THREAD_OWNERS_BASE_NS: tuple[str, ...] = ("thread_owners",)
_MEMORY_BASE_NS: tuple[str, ...] = ("memory",)
_EXTENSIONS_BASE_NS: tuple[str, ...] = ("extensions_config",)


def user_threads_namespace(user_id: str) -> tuple[str, ...]:
    """Return the Store namespace for *user_id*'s thread records.

    Example::

        user_threads_namespace("abc-123") == ("threads", "user:abc-123")
    """
    return (*_THREADS_BASE_NS, f"user:{validate_user_id(user_id)}")


def user_thread_owners_namespace(user_id: str) -> tuple[str, ...]:
    """Return the Store namespace for *user_id*'s thread ownership mappings.

    Example::

        user_thread_owners_namespace("abc-123") == ("thread_owners", "user:abc-123")
    """
    return (*_THREAD_OWNERS_BASE_NS, f"user:{validate_user_id(user_id)}")


def user_memory_namespace(user_id: str) -> tuple[str, ...]:
    """Return the Store namespace for *user_id*'s memory records.

    Example::

        user_memory_namespace("abc-123") == ("memory", "user:abc-123")
    """
    return (*_MEMORY_BASE_NS, f"user:{validate_user_id(user_id)}")


def user_extensions_namespace(user_id: str) -> tuple[str, ...]:
    """Return the Store namespace for *user_id*'s extensions config.

    Example::

        user_extensions_namespace("abc-123") == ("extensions_config", "user:abc-123")
    """
    return (*_EXTENSIONS_BASE_NS, f"user:{validate_user_id(user_id)}")


# ---------------------------------------------------------------------------
# Filesystem label helper
# ---------------------------------------------------------------------------


def validated_user_id_for_path(user_id: str) -> str:
    """Return *user_id* after validation, ready to pass to ``Paths`` methods.

    This is a thin wrapper around :func:`validate_user_id` that makes the
    intent explicit at call sites: the caller is about to use the ID in a
    filesystem path.

    Raises:
        ValueError: Same conditions as :func:`validate_user_id`.
    """
    return validate_user_id(user_id)
