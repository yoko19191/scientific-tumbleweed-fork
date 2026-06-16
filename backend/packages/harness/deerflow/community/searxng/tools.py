from __future__ import annotations

import json
import logging

from langchain.tools import tool

from deerflow.community.citations import canonical_web_result
from deerflow.config import get_app_config

from .searxng_client import SearxngClient

logger = logging.getLogger(__name__)


def _get_tool_extras() -> dict:
    config = get_app_config().get_tool_config("web_search")
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


def _coerce_str(value: object, *, default: str) -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _coerce_categories(value: object) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, str):
        categories = [part.strip() for part in value.split(",")]
    elif isinstance(value, list):
        categories = [str(part).strip() for part in value]
    else:
        return None
    return [category for category in categories if category] or None


def _get_searxng_client() -> SearxngClient:
    extras = _get_tool_extras()
    base_url = _coerce_str(extras.get("base_url"), default="http://localhost:8088")
    timeout_s = _coerce_float(extras.get("timeout_s"), default=30.0)
    return SearxngClient(base_url=base_url, timeout_s=timeout_s)


@tool("web_search", parse_docstring=True)
async def web_search_tool(query: str, max_results: int = 5) -> str:
    """Search the web using a configured SearXNG instance.

    Args:
        query: The query to search for.
        max_results: Maximum number of search results to return. Default is 5.
    """
    try:
        extras = _get_tool_extras()
        max_results = _coerce_int(extras.get("max_results", max_results), default=max_results)
        language = _coerce_str(extras.get("language"), default="auto")
        categories = _coerce_categories(extras.get("categories"))

        client = _get_searxng_client()
        results = await client.search(
            query,
            max_results=max_results,
            categories=categories,
            language=language,
        )
    except Exception as exc:
        logger.error("SearXNG search failed: %s", exc)
        return json.dumps({"error": str(exc), "query": query}, ensure_ascii=False)

    normalized_results = []
    for item in results:
        title = item.get("title", "") or ""
        url = item.get("url", "") or ""
        snippet = item.get("content", "") or item.get("snippet", "") or ""
        normalized_results.append(
            {
                "title": title,
                "url": url,
                "content": snippet,
                **canonical_web_result(
                    title=title,
                    url=url,
                    snippet=snippet,
                    provider="searxng",
                ),
            }
        )

    return json.dumps(
        {
            "query": query,
            "total_results": len(normalized_results),
            "results": normalized_results,
        },
        indent=2,
        ensure_ascii=False,
    )
