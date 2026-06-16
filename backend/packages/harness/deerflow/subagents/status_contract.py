"""Structured subagent status contract shared by API serializers."""

from __future__ import annotations

from typing import Any, Literal, TypedDict

SUBAGENT_STATUS_KEY = "subagent_status"

SubagentStatusValue = Literal["in_progress", "completed", "failed", "cancelled", "timed_out"]

SUCCESS_PREFIX = "Task Succeeded. Result:"
FAILURE_PREFIX = "Task failed."
TIMEOUT_PREFIX = "Task timed out"
CANCELLED_PREFIX = "Task cancelled by user."
POLLING_TIMEOUT_PREFIX = "Task polling timed out"


class SubagentStatusPayload(TypedDict, total=False):
    status: SubagentStatusValue
    result: str
    error: str


def parse_subagent_status_from_text(content: Any) -> SubagentStatusPayload | None:
    """Build a structured subagent status from the historical task output text."""

    if not isinstance(content, str):
        return None

    text = content.strip()
    if text.startswith(SUCCESS_PREFIX):
        return {
            "status": "completed",
            "result": text.removeprefix(SUCCESS_PREFIX).strip(),
        }

    if text.startswith(FAILURE_PREFIX):
        return {
            "status": "failed",
            "error": text.removeprefix(FAILURE_PREFIX).strip(),
        }

    if text.startswith(CANCELLED_PREFIX):
        return {
            "status": "cancelled",
            "error": text,
        }

    if text.startswith(TIMEOUT_PREFIX) or text.startswith(POLLING_TIMEOUT_PREFIX):
        return {
            "status": "timed_out",
            "error": text,
        }

    if text.startswith("Error:"):
        return {
            "status": "failed",
            "error": text,
        }

    return None


def stamp_subagent_status(message: dict[str, Any]) -> dict[str, Any]:
    """Return *message* with ``additional_kwargs.subagent_status`` when known."""

    if message.get("type") not in {"tool", "tool_message"}:
        return message

    additional_kwargs = message.get("additional_kwargs")
    if isinstance(additional_kwargs, dict) and SUBAGENT_STATUS_KEY in additional_kwargs:
        return message

    payload = parse_subagent_status_from_text(message.get("content"))
    if payload is None:
        return message

    stamped = dict(message)
    stamped["additional_kwargs"] = {
        **(additional_kwargs if isinstance(additional_kwargs, dict) else {}),
        SUBAGENT_STATUS_KEY: payload,
    }
    return stamped
