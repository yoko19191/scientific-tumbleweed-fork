"""Canonical serialization for LangChain / LangGraph objects.

Provides a single source of truth for converting LangChain message
objects, Pydantic models, and LangGraph state dicts into plain
JSON-serialisable Python structures.

Consumers: ``deerflow.runtime.runs.worker`` (SSE publishing) and
``app.gateway.routers.threads`` (REST responses).
"""

from __future__ import annotations

from typing import Any

from deerflow.subagents.status_contract import stamp_subagent_status


def serialize_lc_object(obj: Any) -> Any:
    """Recursively serialize a LangChain object to a JSON-serialisable dict."""
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return stamp_subagent_status({k: serialize_lc_object(v) for k, v in obj.items()})
    if isinstance(obj, (list, tuple)):
        return [serialize_lc_object(item) for item in obj]
    # Pydantic v2
    if hasattr(obj, "model_dump"):
        try:
            dumped = obj.model_dump()
            if isinstance(dumped, dict):
                return stamp_subagent_status(dumped)
            return dumped
        except Exception:
            pass
    # Pydantic v1 / older objects
    if hasattr(obj, "dict"):
        try:
            dumped = obj.dict()
            if isinstance(dumped, dict):
                return stamp_subagent_status(dumped)
            return dumped
        except Exception:
            pass
    # Last resort
    try:
        return str(obj)
    except Exception:
        return repr(obj)


def serialize_channel_values(channel_values: dict[str, Any]) -> dict[str, Any]:
    """Serialize channel values, stripping internal LangGraph keys.

    Internal keys like ``__pregel_*`` and ``__interrupt__`` are removed
    to match what the LangGraph Platform API returns.
    """
    result: dict[str, Any] = {}
    for key, value in channel_values.items():
        if key.startswith("__pregel_") or key == "__interrupt__":
            continue
        result[key] = serialize_lc_object(value)
    return result


def _hidden_data_url_image_block(block: Any) -> bool:
    if not isinstance(block, dict):
        return False
    if block.get("type") != "image_url":
        return False
    image_url = block.get("image_url")
    if not isinstance(image_url, dict):
        return False
    url = image_url.get("url")
    return isinstance(url, str) and url.startswith("data:")


def strip_data_url_image_blocks(messages: Any) -> Any:
    """Remove hidden ``data:`` image blocks from serialized messages.

    Hidden view-image messages must stay in checkpoints and SSE/internal state
    for model context, but REST state/history responses should not replay large
    base64 image payloads back to clients.
    """
    if not isinstance(messages, list):
        return messages

    stripped_messages: list[Any] = []
    for message in messages:
        if not isinstance(message, dict):
            stripped_messages.append(message)
            continue

        additional_kwargs = message.get("additional_kwargs") or {}
        hidden = isinstance(additional_kwargs, dict) and additional_kwargs.get("hide_from_ui") is True
        content = message.get("content")
        if not hidden or not isinstance(content, list):
            stripped_messages.append(dict(message))
            continue

        cleaned = [block for block in content if not _hidden_data_url_image_block(block)]
        message_copy = dict(message)
        message_copy["content"] = cleaned
        stripped_messages.append(message_copy)

    return stripped_messages


def serialize_channel_values_for_api(channel_values: dict[str, Any]) -> dict[str, Any]:
    """Serialize channel values for REST APIs, hiding bulky hidden images."""
    result = serialize_channel_values(channel_values)
    if "messages" in result:
        result["messages"] = strip_data_url_image_blocks(result["messages"])
    return result


def serialize_messages_tuple(obj: Any) -> Any:
    """Serialize a messages-mode tuple ``(chunk, metadata)``."""
    if isinstance(obj, tuple) and len(obj) == 2:
        chunk, metadata = obj
        return [serialize_lc_object(chunk), metadata if isinstance(metadata, dict) else {}]
    return serialize_lc_object(obj)


def serialize(obj: Any, *, mode: str = "") -> Any:
    """Serialize LangChain objects with mode-specific handling.

    * ``messages`` — obj is ``(message_chunk, metadata_dict)``
    * ``values`` — obj is the full state dict; ``__pregel_*`` keys stripped
    * everything else — recursive ``model_dump()`` / ``dict()`` fallback
    """
    if mode == "messages":
        return serialize_messages_tuple(obj)
    if mode == "values":
        return serialize_channel_values(obj) if isinstance(obj, dict) else serialize_lc_object(obj)
    return serialize_lc_object(obj)
