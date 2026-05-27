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
        total_input_tokens: int = 0,
        total_output_tokens: int = 0,
        total_tokens: int = 0,
        llm_call_count: int = 0,
        lead_agent_tokens: int = 0,
        subagent_tokens: int = 0,
        middleware_tokens: int = 0,
        message_count: int = 0,
        last_ai_message: str | None = None,
        first_human_message: str | None = None,
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

    async def update_run_completion(self, run_id: str, **kwargs: Any) -> None:
        """Persist final run token/message summary."""
        return None

    async def update_run_progress(self, run_id: str, **kwargs: Any) -> None:
        """Persist a best-effort running token/message snapshot."""
        return None

    async def aggregate_tokens_by_thread(self, thread_id: str, *, include_active: bool = False) -> dict[str, Any]:
        """Aggregate token usage for runs in a thread."""
        return {
            "total_tokens": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_runs": 0,
            "by_model": {},
            "by_caller": {"lead_agent": 0, "subagent": 0, "middleware": 0},
        }

    @abc.abstractmethod
    async def delete(self, run_id: str) -> None:
        """Delete a persisted run row."""
