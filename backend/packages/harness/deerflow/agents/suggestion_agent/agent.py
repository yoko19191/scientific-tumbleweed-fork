"""Follow-up suggestion agent module."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable, Sequence
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from deerflow.models import create_chat_model
from deerflow.prompts.render import render_template

logger = logging.getLogger(__name__)


def _strip_markdown_code_fence(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if len(lines) >= 3 and lines[0].startswith("```") and lines[-1].startswith("```"):
        return "\n".join(lines[1:-1]).strip()
    return stripped


def _parse_json_string_list(text: str) -> list[str] | None:
    candidate = _strip_markdown_code_fence(text)
    start = candidate.find("[")
    end = candidate.rfind("]")
    if start == -1 or end == -1 or end <= start:
        return None
    candidate = candidate[start : end + 1]
    try:
        data = json.loads(candidate)
    except Exception:
        return None
    if not isinstance(data, list):
        return None
    out: list[str] = []
    for item in data:
        if not isinstance(item, str):
            continue
        s = item.strip()
        if not s:
            continue
        out.append(s)
    return out


def _extract_response_text(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") in {"text", "output_text"}:
                text = block.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(parts) if parts else ""
    if content is None:
        return ""
    return str(content)


def _message_value(message: object, field: str) -> str:
    if isinstance(message, dict):
        value = message.get(field)
    else:
        value = getattr(message, field, None)
    return value if isinstance(value, str) else ""


def _format_conversation(messages: Sequence[object]) -> str:
    parts: list[str] = []
    for message in messages:
        role = _message_value(message, "role").strip().lower()
        content = _message_value(message, "content").strip()
        if role in ("user", "human"):
            parts.append(f"User: {content}")
        elif role in ("assistant", "ai"):
            parts.append(f"Assistant: {content}")
        else:
            parts.append(f"{_message_value(message, 'role')}: {content}")
    return "\n".join(parts).strip()


def _build_suggestion_prompt(n: int) -> str:
    return render_template("agents/suggestion.j2", n=n)


async def generate_suggestions(
    messages: Sequence[object],
    n: int,
    model_name: str | None = None,
    *,
    model_factory: Callable[..., Any] = create_chat_model,
) -> list[str]:
    """Generate short follow-up questions from recent conversation messages."""
    if not messages:
        return []

    conversation = _format_conversation(messages)
    if not conversation:
        return []

    user_content = f"Conversation Context:\n{conversation}\n\nGenerate {n} follow-up questions"

    try:
        model = model_factory(name=model_name, thinking_enabled=False)
        response = await model.ainvoke(
            [
                SystemMessage(content=_build_suggestion_prompt(n)),
                HumanMessage(content=user_content),
            ],
            config={"run_name": "suggest_agent"},
        )
        raw = _extract_response_text(response.content)
        suggestions = _parse_json_string_list(raw) or []
        cleaned = [s.replace("\n", " ").strip() for s in suggestions if s.strip()]
        return cleaned[:n]
    except Exception as exc:
        logger.exception("Failed to generate suggestions: err=%s", exc)
        return []
