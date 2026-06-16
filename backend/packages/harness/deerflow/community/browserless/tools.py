from __future__ import annotations

import asyncio
import logging

from langchain.tools import tool

from deerflow.community.citations import format_fetched_document
from deerflow.config import get_app_config
from deerflow.utils.readability import ReadabilityExtractor

from .browserless_client import BrowserlessClient

logger = logging.getLogger(__name__)

_readability_extractor = ReadabilityExtractor()


def _get_tool_extras() -> dict:
    config = get_app_config().get_tool_config("web_fetch")
    if config is None:
        return {}
    return config.model_extra or {}


def _coerce_int(value: object, *, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _coerce_float(value: object, *, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _coerce_str(value: object, *, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _coerce_string_list(value: object) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, str):
        values = [part.strip() for part in value.split(",")]
    elif isinstance(value, list):
        values = [str(part).strip() for part in value]
    else:
        return None
    return [item for item in values if item] or None


def _get_browserless_client() -> BrowserlessClient:
    extras = _get_tool_extras()
    return BrowserlessClient(
        base_url=_coerce_str(extras.get("base_url"), default="http://localhost:3032"),
        token=_coerce_str(extras.get("token")),
        timeout_s=_coerce_float(extras.get("timeout_s"), default=30.0),
    )


@tool("web_fetch", parse_docstring=True)
async def web_fetch_tool(url: str) -> str:
    """Fetch the contents of a web page at a given URL using Browserless headless Chrome.
    Only fetch EXACT URLs that have been provided directly by the user or have been returned in results from the web_search and web_fetch tools.
    This tool can NOT access content that requires authentication, such as private Google Docs or pages behind login walls.
    Do NOT add www. to URLs that do NOT have them.
    URLs must include the schema: https://example.com is a valid URL while example.com is an invalid URL.

    Args:
        url: The URL to fetch the contents of.
    """
    try:
        extras = _get_tool_extras()
        client = _get_browserless_client()
        html = await client.fetch_html(
            url=url,
            wait_for_event=_coerce_str(extras.get("wait_for_event")),
            wait_for_timeout_ms=_coerce_int(extras.get("wait_for_timeout_ms"), default=0),
            wait_for_selector=_coerce_str(extras.get("wait_for_selector")),
            wait_for_selector_timeout_ms=_coerce_int(
                extras.get("wait_for_selector_timeout_ms"),
                default=5000,
            ),
            reject_resource_types=_coerce_string_list(extras.get("reject_resource_types")),
            reject_request_pattern=_coerce_string_list(extras.get("reject_request_pattern")),
        )
        if html.startswith("Error:"):
            return html

        article = await asyncio.to_thread(_readability_extractor.extract_article, html)
        return format_fetched_document(
            title=article.title,
            url=url,
            provider="browserless",
            content=article.to_markdown(including_title=False),
        )
    except Exception as exc:
        logger.error("Error in Browserless web_fetch_tool: %s", exc)
        return f"Error: {str(exc)}"
