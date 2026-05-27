"""Helpers for summarizing run token usage."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage, HumanMessage

from deerflow.agents.middlewares.token_usage_middleware import SUBAGENT_USAGE_KEY


def _message_type(message: Any) -> str | None:
    if isinstance(message, AIMessage):
        return "ai"
    if isinstance(message, HumanMessage):
        return "human"
    if isinstance(message, dict):
        value = message.get("type")
        return str(value) if value is not None else None
    value = getattr(message, "type", None)
    return str(value) if value is not None else None


def _content_text(message: Any) -> str | None:
    content = message.get("content") if isinstance(message, dict) else getattr(message, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and isinstance(block.get("text"), str):
                parts.append(block["text"])
        return "\n".join(parts) if parts else None
    return str(content) if content is not None else None


def _usage_metadata(message: Any) -> dict[str, Any]:
    usage = message.get("usage_metadata") if isinstance(message, dict) else getattr(message, "usage_metadata", None)
    return dict(usage) if isinstance(usage, dict) else {}


def _additional_kwargs(message: Any) -> dict[str, Any]:
    additional_kwargs = message.get("additional_kwargs") if isinstance(message, dict) else getattr(message, "additional_kwargs", None)
    return dict(additional_kwargs) if isinstance(additional_kwargs, dict) else {}


def summarize_messages_token_usage(messages: list[Any] | None) -> dict[str, Any]:
    """Summarize token usage from a list of LangChain or serialized messages."""
    summary: dict[str, Any] = {
        "total_input_tokens": 0,
        "total_output_tokens": 0,
        "total_tokens": 0,
        "llm_call_count": 0,
        "lead_agent_tokens": 0,
        "subagent_tokens": 0,
        "middleware_tokens": 0,
        "message_count": len(messages or []),
        "last_ai_message": None,
        "first_human_message": None,
    }

    for message in messages or []:
        message_type = _message_type(message)
        if message_type == "human" and summary["first_human_message"] is None:
            summary["first_human_message"] = _content_text(message)
            continue
        if message_type != "ai":
            continue

        text = _content_text(message)
        if text:
            summary["last_ai_message"] = text

        usage = _usage_metadata(message)
        input_tokens = usage.get("input_tokens", 0) or 0
        output_tokens = usage.get("output_tokens", 0) or 0
        total_tokens = usage.get("total_tokens", 0) or 0
        if total_tokens <= 0:
            total_tokens = input_tokens + output_tokens
        if total_tokens <= 0:
            continue

        summary["llm_call_count"] += 1
        summary["total_input_tokens"] += input_tokens
        summary["total_output_tokens"] += output_tokens
        summary["total_tokens"] += total_tokens

        additional_kwargs = _additional_kwargs(message)
        subagent_usage = additional_kwargs.get(SUBAGENT_USAGE_KEY)
        subagent_tokens = subagent_usage.get("total_tokens", 0) if isinstance(subagent_usage, dict) else 0
        subagent_tokens = min(subagent_tokens or 0, total_tokens)
        summary["subagent_tokens"] += subagent_tokens
        summary["lead_agent_tokens"] += total_tokens - subagent_tokens

    return summary
