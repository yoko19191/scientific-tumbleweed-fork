from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import pytest

from deerflow.community.searxng import tools
from deerflow.community.searxng.searxng_client import SearxngClient


@pytest.mark.anyio
async def test_searxng_client_sends_json_search_params(monkeypatch):
    captured = {}

    async def fake_get(self, url, *, params, headers):
        captured["url"] = url
        captured["params"] = params
        captured["headers"] = headers
        return httpx.Response(
            200,
            json={
                "results": [
                    {"title": "One", "url": "https://example.com/one", "content": "first"},
                    {"title": "Two", "url": "https://example.com/two", "content": "second"},
                ]
            },
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    client = SearxngClient(base_url="http://searxng.local/", timeout_s=5)
    results = await client.search("query", max_results=1, categories=["general", "news"], language="en")

    assert captured["url"] == "http://searxng.local/search"
    assert captured["params"] == {
        "q": "query",
        "format": "json",
        "language": "en",
        "pageno": 1,
        "limit": 1,
        "categories": "general,news",
    }
    assert captured["headers"]["Accept"] == "application/json"
    assert len(results) == 1


@pytest.mark.anyio
async def test_searxng_tool_returns_citation_results(monkeypatch):
    mock_config = MagicMock()
    mock_config.get_tool_config.return_value = SimpleNamespace(
        model_extra={
            "base_url": "http://searxng.local",
            "categories": "general,news",
            "language": "en",
            "max_results": "2",
            "timeout_s": 7,
        }
    )
    captured = {}

    async def fake_search(self, query, *, max_results, categories, language):
        captured.update(
            {
                "base_url": self.base_url,
                "timeout_s": self.timeout_s,
                "query": query,
                "max_results": max_results,
                "categories": categories,
                "language": language,
            }
        )
        return [
            {
                "title": "SearXNG title",
                "url": "https://example.com/searxng",
                "content": "SearXNG evidence.",
            }
        ]

    monkeypatch.setattr(tools, "get_app_config", lambda: mock_config)
    monkeypatch.setattr(SearxngClient, "search", fake_search)

    result = json.loads(await tools.web_search_tool.ainvoke({"query": "example"}))

    assert captured == {
        "base_url": "http://searxng.local",
        "timeout_s": 7.0,
        "query": "example",
        "max_results": 2,
        "categories": ["general", "news"],
        "language": "en",
    }
    item = result["results"][0]
    assert item["title"] == "SearXNG title"
    assert item["url"] == "https://example.com/searxng"
    assert item["content"] == "SearXNG evidence."
    assert item["citationUrl"] == "https://example.com/searxng"
    assert item["citationProvider"] == "searxng"
