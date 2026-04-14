"""Thread ownership service.

Provides functions to bind threads to authenticated users and to verify
ownership before any thread resource is accessed.

Design
------
Ownership mappings are stored in the LangGraph Store under a user-scoped
namespace produced by :func:`app.gateway.user_prefix.user_thread_owners_namespace`.
The key is the ``thread_id``; the value is ``{"user_id": "<uid>", ...}``.

Using a *per-user namespace* means that listing all threads for a user is a
single ``asearch`` call on that user's namespace — no full-table scan needed.

Strict mode
-----------
When the Store is available, every thread access goes through
:func:`require_thread_owner`.  Threads that have no ownership record are
rejected (404) rather than silently allowed.  This prevents cross-user access
via guessed thread IDs.

Client-supplied ``user_id`` in request body / metadata is **never** trusted.
The authenticated user ID always comes from the server-verified session cookie
via :func:`app.gateway.deps.get_current_user_id`.
"""

from __future__ import annotations

import logging
import time

from fastapi import HTTPException, Request

from app.gateway.user_prefix import user_thread_owners_namespace, validate_user_id

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Bind
# ---------------------------------------------------------------------------


async def bind_thread_to_user(store, user_id: str, thread_id: str) -> None:
    """Record that *thread_id* is owned by *user_id*.

    Idempotent: if the mapping already exists with the same *user_id* it is
    left unchanged.  If it exists with a *different* user_id a 403 is raised
    (ownership cannot be transferred).

    Args:
        store: LangGraph Store instance (``app.state.store``).
        user_id: Server-authenticated user ID (already validated).
        thread_id: Thread to bind.

    Raises:
        HTTPException 403: Thread is already owned by a different user.
    """
    uid = validate_user_id(user_id)
    ns = user_thread_owners_namespace(uid)

    existing = await store.aget(ns, thread_id)
    if existing is not None:
        existing_uid = existing.value.get("user_id")
        if existing_uid != uid:
            # Ownership conflict — do not leak the real owner's ID
            raise HTTPException(status_code=403, detail="Thread ownership conflict")
        # Already bound to the same user — idempotent success
        return

    await store.aput(ns, thread_id, {"user_id": uid, "created_at": time.time()})


# ---------------------------------------------------------------------------
# Require owner
# ---------------------------------------------------------------------------


async def require_thread_owner(request: Request, thread_id: str) -> str:
    """Verify the authenticated user owns *thread_id* and return the user ID.

    This function must be called **before** reading checkpoint values, thread
    metadata, uploads, artifacts, or run records.

    Resolution order
    ----------------
    1. Decode the session cookie via :func:`app.gateway.deps.get_current_user_id`
       to obtain the server-authenticated user ID.
    2. Look up the ownership record in the user-scoped Store namespace.
    3. If no record exists → 404 (thread not found or not owned by this user).
    4. If the record's ``user_id`` does not match → 404 (uniform denial, no
       information leak about whether the thread exists for another user).

    Args:
        request: The current FastAPI request.
        thread_id: Thread ID to check.

    Returns:
        The authenticated user ID string.

    Raises:
        HTTPException 401: No valid session cookie.
        HTTPException 404: Thread not found or not owned by the current user.
        HTTPException 503: Store not available.
    """
    from app.gateway.deps import get_current_user_id as _get_current_user_id
    from app.gateway.deps import get_store

    user_id = await _get_current_user_id(request)
    store = get_store(request)

    if store is None:
        raise HTTPException(status_code=503, detail="Store not available")

    ns = user_thread_owners_namespace(user_id)
    item = await store.aget(ns, thread_id)

    if item is None or item.value.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail=f"Thread {thread_id} not found")

    return user_id


# ---------------------------------------------------------------------------
# Get owner (non-raising)
# ---------------------------------------------------------------------------


async def get_thread_owner(store, user_id: str, thread_id: str) -> str | None:
    """Return the owner user_id for *thread_id* if it matches *user_id*, else None.

    Non-raising variant used for conditional logic (e.g. idempotency checks).
    """
    uid = validate_user_id(user_id)
    ns = user_thread_owners_namespace(uid)
    item = await store.aget(ns, thread_id)
    if item is None:
        return None
    stored_uid = item.value.get("user_id")
    return stored_uid if stored_uid == uid else None
