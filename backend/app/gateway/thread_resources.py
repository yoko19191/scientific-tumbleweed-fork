"""Authenticated Gateway access to user-scoped thread resources."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from fastapi import HTTPException, Request

from app.gateway.thread_ownership import require_thread_owner
from app.gateway.user_prefix import user_thread_owners_namespace, user_threads_namespace
from deerflow.config.paths import Paths, get_paths

LEGACY_THREADS_NS: tuple[str, ...] = ("threads",)
LEGACY_THREAD_OWNERS_NS: tuple[str, ...] = ("thread_owners",)


def user_thread_records_namespace(user_id: str) -> tuple[str, ...]:
    """Return the Store namespace for thread records owned by *user_id*."""
    return user_threads_namespace(user_id)


def user_thread_ownership_namespace(user_id: str) -> tuple[str, ...]:
    """Return the Store namespace for ownership records owned by *user_id*."""
    return user_thread_owners_namespace(user_id)


def thread_records_namespace(user_id: str | None) -> tuple[str, ...]:
    """Return the authenticated user's thread namespace or the legacy namespace."""
    return user_thread_records_namespace(user_id) if user_id else LEGACY_THREADS_NS


@dataclass(frozen=True)
class AuthenticatedThreadResource:
    """Stable interface for Gateway routes that touch a thread's user resources."""

    thread_id: str
    user_id: str
    paths: Paths = field(default_factory=get_paths)

    def resolve_virtual_path(self, virtual_path: str) -> Path:
        """Resolve a sandbox virtual path under this authenticated user's thread."""
        try:
            return self.paths.resolve_virtual_path(self.thread_id, virtual_path, self.user_id)
        except ValueError as exc:
            status = 403 if "traversal" in str(exc) else 400
            raise HTTPException(status_code=status, detail=str(exc)) from exc

    def uploads_dir(self) -> Path:
        """Return this thread's user-scoped uploads directory."""
        return self.paths.resolve_uploads_dir(self.thread_id, self.user_id)

    def delete_local_data(self) -> None:
        """Delete only this user's local filesystem data for the thread."""
        self.paths.delete_thread_dir(self.thread_id, self.user_id)


async def get_authenticated_thread_resource(
    request: Request,
    thread_id: str,
    *,
    paths: Paths | None = None,
) -> AuthenticatedThreadResource:
    """Verify ownership and return the only route-level interface for thread files."""
    user_id = await require_thread_owner(request, thread_id)
    return AuthenticatedThreadResource(thread_id=thread_id, user_id=user_id, paths=paths or get_paths())


async def search_thread_ownerships(store, user_id: str, *, limit: int = 10_000):
    """Return ownership records in the authenticated user's namespace."""
    return await store.asearch(user_thread_ownership_namespace(user_id), limit=limit)


async def get_user_thread_record(store, user_id: str, thread_id: str, *, include_legacy: bool = False) -> dict | None:
    """Fetch a user-scoped thread record, optionally falling back to legacy data."""
    item = await store.aget(user_thread_records_namespace(user_id), thread_id)
    if item is not None:
        return item.value
    if include_legacy:
        item = await store.aget(LEGACY_THREADS_NS, thread_id)
        if item is not None:
            return item.value
    return None


async def put_user_thread_record(store, user_id: str, record: dict) -> None:
    """Write a thread record into the authenticated user's namespace."""
    await store.aput(user_thread_records_namespace(user_id), record["thread_id"], record)


async def delete_user_thread_record(store, user_id: str, thread_id: str) -> None:
    """Delete a thread record from the authenticated user's namespace."""
    await store.adelete(user_thread_records_namespace(user_id), thread_id)


async def delete_thread_ownership(store, user_id: str, thread_id: str) -> None:
    """Delete a thread ownership record from the authenticated user's namespace."""
    await store.adelete(user_thread_ownership_namespace(user_id), thread_id)
