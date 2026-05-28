"""Checkpoint read helpers used by run-facing APIs."""

from __future__ import annotations

from typing import Any

from deerflow.runtime.serialization import serialize_channel_values

ROOT_CHECKPOINT_NS = ""


def thread_checkpoint_config(
    thread_id: str,
    *,
    checkpoint_id: str | None = None,
    checkpoint_ns: str = ROOT_CHECKPOINT_NS,
) -> dict[str, dict[str, str]]:
    """Return the canonical root-graph checkpointer config for a thread."""
    configurable = {"thread_id": thread_id, "checkpoint_ns": checkpoint_ns}
    if checkpoint_id:
        configurable["checkpoint_id"] = checkpoint_id
    return {"configurable": configurable}


def checkpoint_channel_values(checkpoint_tuple: Any) -> dict[str, Any]:
    """Extract raw channel values from a LangGraph checkpoint tuple."""
    if checkpoint_tuple is None:
        return {}
    checkpoint = getattr(checkpoint_tuple, "checkpoint", {}) or {}
    if not isinstance(checkpoint, dict):
        return {}
    channel_values = checkpoint.get("channel_values", {})
    return channel_values if isinstance(channel_values, dict) else {}


async def read_thread_checkpoint_values(
    checkpointer: Any,
    thread_id: str,
    *,
    checkpoint_id: str | None = None,
    checkpoint_ns: str = ROOT_CHECKPOINT_NS,
) -> dict[str, Any] | None:
    """Read raw channel values from the latest checkpoint for a thread."""
    checkpoint_tuple = await checkpointer.aget_tuple(
        thread_checkpoint_config(
            thread_id,
            checkpoint_id=checkpoint_id,
            checkpoint_ns=checkpoint_ns,
        )
    )
    if checkpoint_tuple is None:
        return None
    return checkpoint_channel_values(checkpoint_tuple)


async def read_thread_final_state(
    checkpointer: Any,
    thread_id: str,
    *,
    checkpoint_ns: str = ROOT_CHECKPOINT_NS,
) -> dict[str, Any] | None:
    """Read the serialized final state for a completed thread run."""
    channel_values = await read_thread_checkpoint_values(
        checkpointer,
        thread_id,
        checkpoint_ns=checkpoint_ns,
    )
    if channel_values is None:
        return None
    return serialize_channel_values(channel_values)
