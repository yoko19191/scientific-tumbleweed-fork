"""
Web Search Tool - Search the web using the official Brave Search API.
"""

from __future__ import annotations

import json
import logging
import os

import httpx
from langchain.tools import tool

from deerflow.community.citations import canonical_web_result
from deerflow.config import get_app_config

logger = logging.getLogger(__name__)

_BRAVE_ENDPOINT = "https://api.search.brave.com/res/v1/web/search"
_DEFAULT_MAX_RESULTS = 5
_BRAVE_MAX_COUNT = 20
_api_key_warned = False


def _get_tool_extras() -> dict:
    config = get_app_config().get_tool_config("web_search")
    if config is None:
        return {}
    return config.model_extra or {}


def _get_api_key() -> str | None:
    api_key = _get_tool_extras().get("api_key")
    if isinstance(api_key, str) and api_key.strip():
        return api_key.strip()
    return os.getenv("BRAVE_SEARCH_API_KEY")


def _coerce_max_results(value: object, *, default: int = _DEFAULT_MAX_RESULTS) -> int:
    try:
        coerced = int(value)
    except (TypeError, ValueError):
        logger.warning("Invalid Brave Search max_results=%r; using default %s", value, default)
        coerced = default
    return max(1, min(coerced, _BRAVE_MAX_COUNT))


@tool("web_search", parse_docstring=True)
def web_search_tool(query: str, max_results: int = _DEFAULT_MAX_RESULTS) -> str:
    """Search the web for information using Brave Search.

    Args:
        query: Search keywords describing what you want to find. Be specific for better results.
        max_results: Maximum number of search results to return. Default is 5.
    """
    global _api_key_warned

    extras = _get_tool_extras()
    max_results = extras.get("max_results", max_results)
    count = _coerce_max_results(max_results)

    api_key = _get_api_key()
    if not api_key:
        if not _api_key_warned:
            _api_key_warned = True
            logger.warning("Brave Search API key is not set. Set BRAVE_SEARCH_API_KEY or web_search.api_key.")
        return json.dumps(
            {"error": "BRAVE_SEARCH_API_KEY is not configured", "query": query},
            ensure_ascii=False,
        )

    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": api_key,
    }
    params = {"q": query, "count": count, "text_decorations": False}

    try:
        with httpx.Client(timeout=30) as client:
            response = client.get(_BRAVE_ENDPOINT, headers=headers, params=params)
        response.raise_for_status()
        payload = response.json()
    except httpx.HTTPStatusError as exc:
        logger.error("Brave Search API returned HTTP %s: %s", exc.response.status_code, exc.response.text)
        return json.dumps(
            {"error": f"Brave Search API error: HTTP {exc.response.status_code}", "query": query},
            ensure_ascii=False,
        )
    except Exception as exc:
        logger.error("Brave search failed: %s: %s", type(exc).__name__, exc)
        return json.dumps({"error": str(exc), "query": query}, ensure_ascii=False)

    web_results = (payload.get("web") or {}).get("results", [])
    if not web_results:
        return json.dumps({"error": "No results found", "query": query}, ensure_ascii=False)

    normalized_results = []
    for item in web_results:
        title = item.get("title", "") or ""
        url = item.get("url", "") or ""
        snippet = item.get("description", "") or ""
        normalized_results.append(
            {
                "title": title,
                "url": url,
                "content": snippet,
                **canonical_web_result(
                    title=title,
                    url=url,
                    snippet=snippet,
                    provider="brave",
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
