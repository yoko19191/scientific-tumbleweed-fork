"""Thread-title agent module."""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from deerflow.models import create_chat_model
from deerflow.prompts.render import render_template

if TYPE_CHECKING:
    from deerflow.config.app_config import AppConfig
    from deerflow.config.title_config import TitleConfig

logger = logging.getLogger(__name__)

DEFAULT_TITLE_PROMPT_TEMPLATE = "Generate a concise title (max {max_words} words) for this conversation.\nUser: {user_msg}\nAssistant: {assistant_msg}\n\nReturn ONLY the title, no quotes, no explanation."


def normalize_content(content: object) -> str:
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = [normalize_content(item) for item in content]
        return "\n".join(part for part in parts if part)

    if isinstance(content, dict):
        content_type = content.get("type")
        if content_type in ("thinking", "reasoning"):
            return ""

        text_value = content.get("text")
        if isinstance(text_value, str):
            return text_value

        nested_content = content.get("content")
        if nested_content is not None:
            return normalize_content(nested_content)

    return ""


def strip_think_tags(text: str) -> str:
    """Remove <think>...</think> blocks emitted by reasoning models."""
    return re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.IGNORECASE).strip()


def build_title_prompt(user_msg: str, assistant_msg: str, config: TitleConfig) -> str:
    values = {
        "max_words": config.max_words,
        "user_msg": user_msg[:500],
        "assistant_msg": strip_think_tags(assistant_msg[:500]),
    }
    if config.prompt_template == DEFAULT_TITLE_PROMPT_TEMPLATE:
        return render_template("agents/title.j2", **values)
    return config.prompt_template.format(**values)


def parse_title(content: object, config: TitleConfig) -> str:
    title_content = strip_think_tags(normalize_content(content))
    title = title_content.strip().strip('"').strip("'")
    return title[: config.max_chars] if len(title) > config.max_chars else title


def fallback_title(user_msg: str, config: TitleConfig) -> str:
    fallback_chars = min(config.max_chars, 50)
    if len(user_msg) > fallback_chars:
        return user_msg[:fallback_chars].rstrip() + "..."
    return user_msg if user_msg else "New Conversation"


async def generate_title(
    user_msg: str,
    assistant_msg: str,
    config: TitleConfig,
    *,
    app_config: AppConfig | None = None,
    model_factory: Callable[..., Any] = create_chat_model,
) -> str:
    """Generate a title asynchronously, returning a local fallback on failure."""
    prompt = build_title_prompt(user_msg, assistant_msg, config)
    try:
        model_kwargs: dict[str, Any] = {"thinking_enabled": False, "attach_tracing": False}
        if app_config is not None:
            model_kwargs["app_config"] = app_config
        if config.model_name:
            model = model_factory(name=config.model_name, **model_kwargs)
        else:
            model = model_factory(**model_kwargs)
        response = await model.ainvoke(prompt, config={"run_name": "title_agent"})
        title = parse_title(response.content, config)
        if title:
            return title
    except Exception:
        logger.debug("Failed to generate async title; falling back to local title", exc_info=True)
    return fallback_title(user_msg, config)
