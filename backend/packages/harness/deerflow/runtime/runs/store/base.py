"""Abstract interface for run metadata storage."""

from __future__ import annotations

import abc
from typing import Any


class RunStore(abc.ABC):
    """Async persistence interface consumed by RunManager."""

    @abc.abstractmethod
    async def put(
        self,
        run_id: str,
        *,
        thread_id: str,
        assistant_id: str | None = None,
        user_id: str | None = None,
        status: str = "pending",
        on_disconnect: str = "cancel",
        multitask_strategy: str = "reject",
        metadata: dict[str, Any] | None = None,
        kwargs: dict[str, Any] | None = None,
        error: str | None = None,
        model_name: str | None = None,
        created_at: str | None = None,
    ) -> None:
        """Persist a run row."""

    @abc.abstractmethod
    async def get(self, run_id: str, *, user_id: str | None = None) -> dict[str, Any] | None:
        """Return a run row by ID."""

    @abc.abstractmethod
    async def list_by_thread(
        self,
        thread_id: str,
        *,
        user_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Return run rows for a thread, newest first."""

    @abc.abstractmethod
    async def update_status(self, run_id: str, status: str, *, error: str | None = None) -> None:
        """Update a run status."""

    @abc.abstractmethod
    async def update_model_name(self, run_id: str, model_name: str | None) -> None:
        """Update the model name captured for a run."""

    @abc.abstractmethod
    async def delete(self, run_id: str) -> None:
        """Delete a persisted run row."""
