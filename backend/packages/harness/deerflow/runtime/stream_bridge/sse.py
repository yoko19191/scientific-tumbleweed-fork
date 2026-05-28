"""Server-Sent Events wire-format helpers."""

from __future__ import annotations

import json
from typing import Any


def format_sse_frame(event: str, data: Any, *, event_id: str | None = None) -> str:
    """Format a single LangGraph-compatible SSE frame."""
    payload = json.dumps(data, default=str, ensure_ascii=False)
    parts = [f"event: {event}", f"data: {payload}"]
    if event_id:
        parts.append(f"id: {event_id}")
    parts.append("")
    parts.append("")
    return "\n".join(parts)
