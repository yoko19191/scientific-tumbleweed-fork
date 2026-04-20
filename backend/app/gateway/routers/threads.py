"""Thread CRUD, state, and history endpoints.

Combines the existing thread-local filesystem cleanup with LangGraph
Platform-compatible thread management backed by the checkpointer.

Channel values returned in state responses are serialized through
:func:`deerflow.runtime.serialization.serialize_channel_values` to
ensure LangChain message objects are converted to JSON-safe dicts
matching the LangGraph Platform wire format expected by the
``useStream`` React hook.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.gateway.authz import require_auth
from app.gateway.deps import get_checkpointer, get_optional_user_from_request, get_optional_user_id, get_store
from app.gateway.thread_ownership import bind_thread_to_user, require_thread_owner
from app.gateway.user_prefix import user_thread_owners_namespace, user_threads_namespace
from deerflow.config.paths import Paths, get_paths
from deerflow.runtime import serialize_channel_values

# ---------------------------------------------------------------------------
# Store namespace (legacy global namespaces — kept for backward compat reads)
# ---------------------------------------------------------------------------

THREADS_NS: tuple[str, ...] = ("threads",)
"""Legacy global namespace — new writes use user-scoped namespaces."""

THREAD_OWNERS_NS: tuple[str, ...] = ("thread_owners",)
"""Legacy global namespace — new writes use user-scoped namespaces."""

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/threads", tags=["threads"])


# ---------------------------------------------------------------------------
# Response / request models
# ---------------------------------------------------------------------------


class ThreadDeleteResponse(BaseModel):
    """Response model for thread cleanup."""

    success: bool
    message: str


class ThreadResponse(BaseModel):
    """Response model for a single thread."""

    thread_id: str = Field(description="Unique thread identifier")
    status: str = Field(default="idle", description="Thread status: idle, busy, interrupted, error")
    created_at: str = Field(default="", description="ISO timestamp")
    updated_at: str = Field(default="", description="ISO timestamp")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Thread metadata")
    values: dict[str, Any] = Field(default_factory=dict, description="Current state channel values")
    interrupts: dict[str, Any] = Field(default_factory=dict, description="Pending interrupts")


class BindUserRequest(BaseModel):
    """Request body for binding a user to a thread."""

    thread_id: str = Field(description="Thread ID to bind to the current user")


class ThreadCreateRequest(BaseModel):
    """Request body for creating a thread."""

    thread_id: str | None = Field(default=None, description="Optional thread ID (auto-generated if omitted)")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Initial metadata")


class ThreadSearchRequest(BaseModel):
    """Request body for searching threads."""

    metadata: dict[str, Any] = Field(default_factory=dict, description="Metadata filter (exact match)")
    limit: int = Field(default=100, ge=1, le=1000, description="Maximum results")
    offset: int = Field(default=0, ge=0, description="Pagination offset")
    status: str | None = Field(default=None, description="Filter by thread status")


class ThreadStateResponse(BaseModel):
    """Response model for thread state."""

    values: dict[str, Any] = Field(default_factory=dict, description="Current channel values")
    next: list[str] = Field(default_factory=list, description="Next tasks to execute")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Checkpoint metadata")
    checkpoint: dict[str, Any] = Field(default_factory=dict, description="Checkpoint info")
    checkpoint_id: str | None = Field(default=None, description="Current checkpoint ID")
    parent_checkpoint_id: str | None = Field(default=None, description="Parent checkpoint ID")
    created_at: str | None = Field(default=None, description="Checkpoint timestamp")
    tasks: list[dict[str, Any]] = Field(default_factory=list, description="Interrupted task details")


class ThreadPatchRequest(BaseModel):
    """Request body for patching thread metadata."""

    metadata: dict[str, Any] = Field(default_factory=dict, description="Metadata to merge")


class ThreadStateUpdateRequest(BaseModel):
    """Request body for updating thread state (human-in-the-loop resume)."""

    values: dict[str, Any] | None = Field(default=None, description="Channel values to merge")
    checkpoint_id: str | None = Field(default=None, description="Checkpoint to branch from")
    checkpoint: dict[str, Any] | None = Field(default=None, description="Full checkpoint object")
    as_node: str | None = Field(default=None, description="Node identity for the update")


class HistoryEntry(BaseModel):
    """Single checkpoint history entry."""

    checkpoint_id: str
    parent_checkpoint_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    values: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None
    next: list[str] = Field(default_factory=list)


class ThreadHistoryRequest(BaseModel):
    """Request body for checkpoint history."""

    limit: int = Field(default=10, ge=1, le=100, description="Maximum entries")
    before: str | None = Field(default=None, description="Cursor for pagination")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _delete_thread_data(thread_id: str, paths: Paths | None = None) -> ThreadDeleteResponse:
    """Delete local persisted filesystem data for a thread."""
    path_manager = paths or get_paths()
    try:
        path_manager.delete_thread_dir(thread_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except FileNotFoundError:
        # Not critical — thread data may not exist on disk
        logger.debug("No local thread data to delete for %s", thread_id)
        return ThreadDeleteResponse(success=True, message=f"No local data for {thread_id}")
    except Exception as exc:
        logger.exception("Failed to delete thread data for %s", thread_id)
        raise HTTPException(status_code=500, detail="Failed to delete local thread data.") from exc

    logger.info("Deleted local thread data for %s", thread_id)
    return ThreadDeleteResponse(success=True, message=f"Deleted local thread data for {thread_id}")


async def _store_get(store, thread_id: str, ns: tuple[str, ...] | None = None) -> dict | None:
    """Fetch a thread record from the Store; returns ``None`` if absent."""
    item = await store.aget(ns if ns is not None else THREADS_NS, thread_id)
    return item.value if item is not None else None


async def _store_put(store, record: dict, ns: tuple[str, ...] | None = None) -> None:
    """Write a thread record to the Store."""
    await store.aput(ns if ns is not None else THREADS_NS, record["thread_id"], record)


async def _store_upsert(store, thread_id: str, *, metadata: dict | None = None, values: dict | None = None, ns: tuple[str, ...] | None = None) -> None:
    """Create or refresh a thread record in the Store.

    On creation the record is written with ``status="idle"``.  On update only
    ``updated_at`` (and optionally ``metadata`` / ``values``) are changed so
    that existing fields are preserved.

    ``values`` carries the agent-state snapshot exposed to the frontend
    (currently just ``{"title": "..."}``).
    """
    now = time.time()
    existing = await _store_get(store, thread_id, ns=ns)
    if existing is None:
        await _store_put(
            store,
            {
                "thread_id": thread_id,
                "status": "idle",
                "created_at": now,
                "updated_at": now,
                "metadata": metadata or {},
                "values": values or {},
            },
            ns=ns,
        )
    else:
        val = dict(existing)
        val["updated_at"] = now
        if metadata:
            val.setdefault("metadata", {}).update(metadata)
        if values:
            val.setdefault("values", {}).update(values)
        await _store_put(store, val, ns=ns)


def _derive_thread_status(checkpoint_tuple) -> str:
    """Derive thread status from checkpoint metadata."""
    if checkpoint_tuple is None:
        return "idle"
    pending_writes = getattr(checkpoint_tuple, "pending_writes", None) or []

    # Check for error in pending writes
    for pw in pending_writes:
        if len(pw) >= 2 and pw[1] == "__error__":
            return "error"

    # Check for pending next tasks (indicates interrupt)
    tasks = getattr(checkpoint_tuple, "tasks", None)
    if tasks:
        return "interrupted"

    return "idle"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/bindUser")
@require_auth
async def bind_user(body: BindUserRequest, request: Request) -> dict[str, bool]:
    """Register a user_id <-> thread_id ownership mapping.

    Idempotent: if the mapping already exists with the same user_id, returns
    success without modification.
    """
    from app.gateway.deps import get_current_user_id

    user_id = await get_current_user_id(request)
    store = get_store(request)
    if store is None:
        raise HTTPException(status_code=503, detail="Store not available")

    await bind_thread_to_user(store, user_id, body.thread_id)
    return {"success": True}


@router.get("/listByUser", response_model=list[ThreadResponse])
@require_auth
async def list_by_user(request: Request) -> list[ThreadResponse]:
    """Return only threads owned by the current user.

    Queries the user-scoped ``thread_owners`` namespace for mappings belonging
    to the authenticated user, then enriches each thread with metadata from the
    checkpointer (title, status, timestamps).
    """
    from app.gateway.deps import get_current_user_id

    user_id = await get_current_user_id(request)
    store = get_store(request)
    if store is None:
        return []

    checkpointer = get_checkpointer(request)

    # Fetch ownership mappings from the user-scoped namespace
    owners_ns = user_thread_owners_namespace(user_id)
    try:
        items = await store.asearch(owners_ns, limit=10_000)
    except Exception:
        logger.warning("Store search failed for listByUser", exc_info=True)
        return []

    owned_thread_ids = [item.key for item in items]

    if not owned_thread_ids:
        return []

    results: list[ThreadResponse] = []
    for thread_id in owned_thread_ids:
        # Read thread metadata from the threads namespace
        thread_record = await _store_get(store, thread_id)

        # Read latest checkpoint for status and title
        config = {"configurable": {"thread_id": thread_id, "checkpoint_ns": ""}}
        checkpoint_tuple = None
        try:
            checkpoint_tuple = await checkpointer.aget_tuple(config)
        except Exception:
            logger.debug("Could not read checkpoint for thread %s", thread_id)

        status = _derive_thread_status(checkpoint_tuple) if checkpoint_tuple is not None else "idle"

        # Extract title from checkpoint channel_values
        ckpt_values: dict[str, Any] = {}
        if checkpoint_tuple is not None:
            checkpoint_data = getattr(checkpoint_tuple, "checkpoint", {}) or {}
            channel_values = checkpoint_data.get("channel_values", {})
            if title := channel_values.get("title"):
                ckpt_values["title"] = title

        ckpt_meta = (getattr(checkpoint_tuple, "metadata", {}) or {}) if checkpoint_tuple is not None else {}

        # Prefer thread record timestamps, fall back to checkpoint metadata
        created_at = ""
        updated_at = ""
        metadata: dict[str, Any] = {}

        if thread_record is not None:
            created_at = str(thread_record.get("created_at", ""))
            updated_at = str(thread_record.get("updated_at", ""))
            metadata = thread_record.get("metadata", {})
            # Merge store-level values with checkpoint values
            store_values = thread_record.get("values", {})
            ckpt_values = {**store_values, **ckpt_values}
        else:
            created_at = str(ckpt_meta.get("created_at", ""))
            updated_at = str(ckpt_meta.get("updated_at", ckpt_meta.get("created_at", "")))
            metadata = {k: v for k, v in ckpt_meta.items() if k not in ("created_at", "updated_at", "step", "source", "writes", "parents")}

        results.append(
            ThreadResponse(
                thread_id=thread_id,
                status=status,
                created_at=created_at,
                updated_at=updated_at,
                metadata=metadata,
                values=ckpt_values,
            )
        )

    # Sort by updated_at descending
    results.sort(key=lambda r: r.updated_at, reverse=True)
    return results


@router.delete("/{thread_id}", response_model=ThreadDeleteResponse)
@require_auth
async def delete_thread_data(thread_id: str, request: Request) -> ThreadDeleteResponse:
    """Delete local persisted filesystem data for a thread.

    Cleans DeerFlow-managed thread directories, removes checkpoint data,
    removes the thread record from the Store, and removes the ownership
    mapping from thread_owners.  Verifies the caller owns the thread.
    """
    # Verify ownership — raises 401/404/503 on failure
    user_id = await require_thread_owner(request, thread_id)
    store = get_store(request)

    # Clean local filesystem
    response = _delete_thread_data(thread_id)

    # Remove from Store (best-effort)
    if store is not None:
        threads_ns = user_threads_namespace(user_id)
        try:
            await store.adelete(threads_ns, thread_id)
        except Exception:
            logger.debug("Could not delete store record for thread %s (not critical)", thread_id)

        # Remove ownership mapping (idempotent — no error if absent)
        owners_ns = user_thread_owners_namespace(user_id)
        try:
            await store.adelete(owners_ns, thread_id)
        except Exception:
            logger.debug("Could not delete ownership mapping for thread %s (not critical)", thread_id)

    # Remove checkpoints (best-effort)
    checkpointer = getattr(request.app.state, "checkpointer", None)
    if checkpointer is not None:
        try:
            if hasattr(checkpointer, "adelete_thread"):
                await checkpointer.adelete_thread(thread_id)
        except Exception:
            logger.debug("Could not delete checkpoints for thread %s (not critical)", thread_id)

    return response


@router.post("", response_model=ThreadResponse)
async def create_thread(body: ThreadCreateRequest, request: Request) -> ThreadResponse:
    """Create a new thread.

    The thread record is written to the Store (for fast listing) and an
    empty checkpoint is written to the checkpointer (for state reads).
    Idempotent: returns the existing record when ``thread_id`` already exists.
    Authentication is optional — anonymous threads are allowed.
    """
    store = get_store(request)
    checkpointer = get_checkpointer(request)
    thread_id = body.thread_id or str(uuid.uuid4())
    now = time.time()

    # Resolve optional user identity (anonymous threads are allowed)
    user = await get_optional_user_from_request(request)
    user_id = str(user.id) if user else None
    threads_ns = user_threads_namespace(user_id) if user_id else THREADS_NS

    # Idempotency: return existing record from Store when already present
    if store is not None:
        existing_record = await _store_get(store, thread_id, ns=threads_ns)
        if existing_record is not None:
            return ThreadResponse(
                thread_id=thread_id,
                status=existing_record.get("status", "idle"),
                created_at=str(existing_record.get("created_at", "")),
                updated_at=str(existing_record.get("updated_at", "")),
                metadata=existing_record.get("metadata", {}),
            )

    # Write thread record to Store
    if store is not None:
        try:
            await _store_put(
                store,
                {
                    "thread_id": thread_id,
                    "status": "idle",
                    "created_at": now,
                    "updated_at": now,
                    "metadata": body.metadata,
                },
                ns=threads_ns,
            )
        except Exception:
            logger.exception("Failed to write thread %s to store", thread_id)
            raise HTTPException(status_code=500, detail="Failed to create thread")

    # Bind thread to user if authenticated
    if store is not None and user_id is not None:
        try:
            await bind_thread_to_user(store, user_id, thread_id)
        except HTTPException:
            # 403 ownership conflict — re-raise; other errors are non-fatal
            raise
        except Exception:
            logger.debug("Failed to bind thread %s to user %s (non-fatal)", thread_id, user_id)

    # Write an empty checkpoint so state endpoints work immediately
    config = {"configurable": {"thread_id": thread_id, "checkpoint_ns": ""}}
    try:
        from langgraph.checkpoint.base import empty_checkpoint

        ckpt_metadata = {
            "step": -1,
            "source": "input",
            "writes": None,
            "parents": {},
            **body.metadata,
            "created_at": now,
        }
        await checkpointer.aput(config, empty_checkpoint(), ckpt_metadata, {})
    except Exception:
        logger.exception("Failed to create checkpoint for thread %s", thread_id)
        raise HTTPException(status_code=500, detail="Failed to create thread")

    logger.info("Thread created: %s", thread_id)
    return ThreadResponse(
        thread_id=thread_id,
        status="idle",
        created_at=str(now),
        updated_at=str(now),
        metadata=body.metadata,
    )


@router.post("/search", response_model=list[ThreadResponse])
async def search_threads(body: ThreadSearchRequest, request: Request) -> list[ThreadResponse]:
    """Search and list threads owned by the authenticated user.

    Returns only threads belonging to the current user via the user-scoped
    Store namespace.  Unauthenticated callers receive an empty list.
    """
    store = get_store(request)

    # Resolve optional user — unauthenticated callers get an empty list
    user_id = get_optional_user_id(request)
    if user_id is None or store is None:
        return []

    threads_ns = user_threads_namespace(user_id)

    merged: dict[str, ThreadResponse] = {}

    try:
        items = await store.asearch(threads_ns, limit=10_000)
    except Exception:
        logger.warning("Store search failed for user %s", user_id, exc_info=True)
        items = []

    for item in items:
        val = item.value
        merged[val["thread_id"]] = ThreadResponse(
            thread_id=val["thread_id"],
            status=val.get("status", "idle"),
            created_at=str(val.get("created_at", "")),
            updated_at=str(val.get("updated_at", "")),
            metadata=val.get("metadata", {}),
            values=val.get("values", {}),
        )

    # -----------------------------------------------------------------------
    # Filter → sort → paginate
    # -----------------------------------------------------------------------
    results = list(merged.values())

    if body.metadata:
        results = [r for r in results if all(r.metadata.get(k) == v for k, v in body.metadata.items())]

    if body.status:
        results = [r for r in results if r.status == body.status]

    results.sort(key=lambda r: r.updated_at, reverse=True)
    return results[body.offset : body.offset + body.limit]


@router.patch("/{thread_id}", response_model=ThreadResponse)
async def patch_thread(thread_id: str, body: ThreadPatchRequest, request: Request) -> ThreadResponse:
    """Merge metadata into a thread record."""
    # Verify ownership — raises 401/404/503 on failure
    user_id = await require_thread_owner(request, thread_id)
    store = get_store(request)

    threads_ns = user_threads_namespace(user_id)
    record = await _store_get(store, thread_id, ns=threads_ns)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Thread {thread_id} not found")

    now = time.time()
    updated = dict(record)
    updated.setdefault("metadata", {}).update(body.metadata)
    updated["updated_at"] = now

    try:
        await _store_put(store, updated, ns=threads_ns)
    except Exception:
        logger.exception("Failed to patch thread %s", thread_id)
        raise HTTPException(status_code=500, detail="Failed to update thread")

    return ThreadResponse(
        thread_id=thread_id,
        status=updated.get("status", "idle"),
        created_at=str(updated.get("created_at", "")),
        updated_at=str(now),
        metadata=updated.get("metadata", {}),
    )


@router.get("/{thread_id}", response_model=ThreadResponse)
async def get_thread(thread_id: str, request: Request) -> ThreadResponse:
    """Get thread info.

    Reads metadata from the Store and derives the accurate execution
    status from the checkpointer.  Falls back to the checkpointer alone
    for threads that pre-date Store adoption (backward compat).
    """
    # Verify ownership — raises 401/404/503 on failure
    user_id = await require_thread_owner(request, thread_id)
    store = get_store(request)
    checkpointer = get_checkpointer(request)

    threads_ns = user_threads_namespace(user_id)
    record: dict | None = None
    if store is not None:
        record = await _store_get(store, thread_id, ns=threads_ns)

    # Derive accurate status from the checkpointer
    config = {"configurable": {"thread_id": thread_id, "checkpoint_ns": ""}}
    try:
        checkpoint_tuple = await checkpointer.aget_tuple(config)
    except Exception:
        logger.exception("Failed to get checkpoint for thread %s", thread_id)
        raise HTTPException(status_code=500, detail="Failed to get thread")

    if record is None and checkpoint_tuple is None:
        raise HTTPException(status_code=404, detail=f"Thread {thread_id} not found")

    # If the thread exists in the checkpointer but not the store (e.g. legacy
    # data), synthesize a minimal store record from the checkpoint metadata.
    if record is None and checkpoint_tuple is not None:
        ckpt_meta = getattr(checkpoint_tuple, "metadata", {}) or {}
        record = {
            "thread_id": thread_id,
            "status": "idle",
            "created_at": ckpt_meta.get("created_at", ""),
            "updated_at": ckpt_meta.get("updated_at", ckpt_meta.get("created_at", "")),
            "metadata": {k: v for k, v in ckpt_meta.items() if k not in ("created_at", "updated_at", "step", "source", "writes", "parents")},
        }

    if record is None:
        raise HTTPException(status_code=404, detail=f"Thread {thread_id} not found")

    status = _derive_thread_status(checkpoint_tuple) if checkpoint_tuple is not None else record.get("status", "idle")
    checkpoint = getattr(checkpoint_tuple, "checkpoint", {}) or {} if checkpoint_tuple is not None else {}
    channel_values = checkpoint.get("channel_values", {})

    return ThreadResponse(
        thread_id=thread_id,
        status=status,
        created_at=str(record.get("created_at", "")),
        updated_at=str(record.get("updated_at", "")),
        metadata=record.get("metadata", {}),
        values=serialize_channel_values(channel_values),
    )


@router.get("/{thread_id}/state", response_model=ThreadStateResponse)
async def get_thread_state(thread_id: str, request: Request) -> ThreadStateResponse:
    """Get the latest state snapshot for a thread.

    Channel values are serialized to ensure LangChain message objects
    are converted to JSON-safe dicts.
    """
    # Verify ownership — raises 401/404/503 on failure
    await require_thread_owner(request, thread_id)
    checkpointer = get_checkpointer(request)

    config = {"configurable": {"thread_id": thread_id, "checkpoint_ns": ""}}
    try:
        checkpoint_tuple = await checkpointer.aget_tuple(config)
    except Exception:
        logger.exception("Failed to get state for thread %s", thread_id)
        raise HTTPException(status_code=500, detail="Failed to get thread state")

    if checkpoint_tuple is None:
        raise HTTPException(status_code=404, detail=f"Thread {thread_id} not found")

    checkpoint = getattr(checkpoint_tuple, "checkpoint", {}) or {}
    metadata = getattr(checkpoint_tuple, "metadata", {}) or {}
    checkpoint_id = None
    ckpt_config = getattr(checkpoint_tuple, "config", {})
    if ckpt_config:
        checkpoint_id = ckpt_config.get("configurable", {}).get("checkpoint_id")

    channel_values = checkpoint.get("channel_values", {})

    parent_config = getattr(checkpoint_tuple, "parent_config", None)
    parent_checkpoint_id = None
    if parent_config:
        parent_checkpoint_id = parent_config.get("configurable", {}).get("checkpoint_id")

    tasks_raw = getattr(checkpoint_tuple, "tasks", []) or []
    next_tasks = [t.name for t in tasks_raw if hasattr(t, "name")]
    tasks = [{"id": getattr(t, "id", ""), "name": getattr(t, "name", "")} for t in tasks_raw]

    return ThreadStateResponse(
        values=serialize_channel_values(channel_values),
        next=next_tasks,
        metadata=metadata,
        checkpoint={"id": checkpoint_id, "ts": str(metadata.get("created_at", ""))},
        checkpoint_id=checkpoint_id,
        parent_checkpoint_id=parent_checkpoint_id,
        created_at=str(metadata.get("created_at", "")),
        tasks=tasks,
    )


@router.post("/{thread_id}/state", response_model=ThreadStateResponse)
async def update_thread_state(thread_id: str, body: ThreadStateUpdateRequest, request: Request) -> ThreadStateResponse:
    """Update thread state (e.g. for human-in-the-loop resume or title rename).

    Writes a new checkpoint that merges *body.values* into the latest
    channel values, then syncs any updated ``title`` field back to the Store
    so that ``/threads/search`` reflects the change immediately.
    """
    # Verify ownership — raises 401/404/503 on failure
    user_id = await require_thread_owner(request, thread_id)
    checkpointer = get_checkpointer(request)
    store = get_store(request)

    # checkpoint_ns must be present in the config for aput — default to ""
    # (the root graph namespace).  checkpoint_id is optional; omitting it
    # fetches the latest checkpoint for the thread.
    read_config: dict[str, Any] = {
        "configurable": {
            "thread_id": thread_id,
            "checkpoint_ns": "",
        }
    }
    if body.checkpoint_id:
        read_config["configurable"]["checkpoint_id"] = body.checkpoint_id

    try:
        checkpoint_tuple = await checkpointer.aget_tuple(read_config)
    except Exception:
        logger.exception("Failed to get state for thread %s", thread_id)
        raise HTTPException(status_code=500, detail="Failed to get thread state")

    if checkpoint_tuple is None:
        raise HTTPException(status_code=404, detail=f"Thread {thread_id} not found")

    # Work on mutable copies so we don't accidentally mutate cached objects.
    checkpoint: dict[str, Any] = dict(getattr(checkpoint_tuple, "checkpoint", {}) or {})
    metadata: dict[str, Any] = dict(getattr(checkpoint_tuple, "metadata", {}) or {})
    channel_values: dict[str, Any] = dict(checkpoint.get("channel_values", {}))

    if body.values:
        channel_values.update(body.values)

    checkpoint["channel_values"] = channel_values
    metadata["updated_at"] = time.time()

    if body.as_node:
        metadata["source"] = "update"
        metadata["step"] = metadata.get("step", 0) + 1
        metadata["writes"] = {body.as_node: body.values}

    # aput requires checkpoint_ns in the config — use the same config used for the
    # read (which always includes checkpoint_ns="").  Do NOT include checkpoint_id
    # so that aput generates a fresh checkpoint ID for the new snapshot.
    write_config: dict[str, Any] = {
        "configurable": {
            "thread_id": thread_id,
            "checkpoint_ns": "",
        }
    }
    try:
        new_config = await checkpointer.aput(write_config, checkpoint, metadata, {})
    except Exception:
        logger.exception("Failed to update state for thread %s", thread_id)
        raise HTTPException(status_code=500, detail="Failed to update thread state")

    new_checkpoint_id: str | None = None
    if isinstance(new_config, dict):
        new_checkpoint_id = new_config.get("configurable", {}).get("checkpoint_id")

    # Sync title changes to the Store so /threads/search reflects them immediately.
    if store is not None and body.values and "title" in body.values:
        try:
            threads_ns = user_threads_namespace(user_id)
            await _store_upsert(store, thread_id, values={"title": body.values["title"]}, ns=threads_ns)
        except Exception:
            logger.debug("Failed to sync title to store for thread %s (non-fatal)", thread_id)

    return ThreadStateResponse(
        values=serialize_channel_values(channel_values),
        next=[],
        metadata=metadata,
        checkpoint_id=new_checkpoint_id,
        created_at=str(metadata.get("created_at", "")),
    )


@router.post("/{thread_id}/history", response_model=list[HistoryEntry])
async def get_thread_history(thread_id: str, body: ThreadHistoryRequest, request: Request) -> list[HistoryEntry]:
    """Get checkpoint history for a thread."""
    # Verify ownership — raises 401/404/503 on failure
    await require_thread_owner(request, thread_id)
    checkpointer = get_checkpointer(request)

    config: dict[str, Any] = {"configurable": {"thread_id": thread_id}}
    if body.before:
        config["configurable"]["checkpoint_id"] = body.before

    entries: list[HistoryEntry] = []
    try:
        async for checkpoint_tuple in checkpointer.alist(config, limit=body.limit):
            ckpt_config = getattr(checkpoint_tuple, "config", {})
            parent_config = getattr(checkpoint_tuple, "parent_config", None)
            metadata = getattr(checkpoint_tuple, "metadata", {}) or {}
            checkpoint = getattr(checkpoint_tuple, "checkpoint", {}) or {}

            checkpoint_id = ckpt_config.get("configurable", {}).get("checkpoint_id", "")
            parent_id = None
            if parent_config:
                parent_id = parent_config.get("configurable", {}).get("checkpoint_id")

            channel_values = checkpoint.get("channel_values", {})

            # Derive next tasks
            tasks_raw = getattr(checkpoint_tuple, "tasks", []) or []
            next_tasks = [t.name for t in tasks_raw if hasattr(t, "name")]

            entries.append(
                HistoryEntry(
                    checkpoint_id=checkpoint_id,
                    parent_checkpoint_id=parent_id,
                    metadata=metadata,
                    values=serialize_channel_values(channel_values),
                    created_at=str(metadata.get("created_at", "")),
                    next=next_tasks,
                )
            )
    except Exception:
        logger.exception("Failed to get history for thread %s", thread_id)
        raise HTTPException(status_code=500, detail="Failed to get thread history")

    return entries
