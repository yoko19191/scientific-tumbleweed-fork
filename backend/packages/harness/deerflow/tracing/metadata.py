"""Langfuse trace-attribute metadata builders."""

from __future__ import annotations

import os
from typing import Any

from deerflow.config import get_enabled_tracing_providers

_DEFAULT_TRACE_NAME = "lead-agent"


def _normalize_tags(tags: list[str] | tuple[str, ...] | None) -> list[str]:
    return [str(tag) for tag in tags or [] if str(tag)]


def build_langfuse_trace_metadata(
    *,
    thread_id: str | None,
    user_id: str | None,
    assistant_id: str | None = None,
    model_name: str | None = None,
    trace_name: str | None = None,
    tags: list[str] | tuple[str, ...] | None = None,
    environment: str | None = None,
) -> dict[str, Any]:
    """Return Langfuse v4 reserved metadata when Langfuse is enabled."""
    if "langfuse" not in get_enabled_tracing_providers():
        return {}

    from deerflow.runtime.user_context import DEFAULT_USER_ID

    effective_tags = _normalize_tags(tags)
    env = environment or os.getenv("DEER_FLOW_ENV") or os.getenv("ENVIRONMENT")
    if env:
        effective_tags.append(f"env:{env}")
    if model_name:
        effective_tags.append(f"model:{model_name}")

    metadata: dict[str, Any] = {
        "langfuse_session_id": thread_id,
        "langfuse_user_id": user_id or DEFAULT_USER_ID,
        "langfuse_trace_name": trace_name or assistant_id or _DEFAULT_TRACE_NAME,
    }
    if effective_tags:
        metadata["langfuse_tags"] = effective_tags
    return metadata


def inject_langfuse_metadata(
    config: dict,
    *,
    thread_id: str | None,
    user_id: str | None,
    assistant_id: str | None = None,
    model_name: str | None = None,
    trace_name: str | None = None,
    environment: str | None = None,
) -> None:
    """Merge Langfuse metadata into RunnableConfig.metadata with setdefault."""
    metadata = config.setdefault("metadata", {})
    for key, value in build_langfuse_trace_metadata(
        thread_id=thread_id,
        user_id=user_id,
        assistant_id=assistant_id,
        model_name=model_name,
        trace_name=trace_name,
        tags=metadata.get("langfuse_tags"),
        environment=environment,
    ).items():
        metadata.setdefault(key, value)
