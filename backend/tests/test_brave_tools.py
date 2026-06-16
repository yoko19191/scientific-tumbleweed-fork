from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx

import deerflow.community.brave.tools as brave_tools


def _config(extra: dict | None = None):
    mock_config = MagicMock()
    mock_config.get_tool_config.return_value = SimpleNamespace(model_extra=extra or {})
    return mock_config


def test_brave_search_requires_api_key(monkeypatch):
    brave_tools._api_key_warned = False
    monkeypatch.delenv("BRAVE_SEARCH_API_KEY", raising=False)
    monkeypatch.setattr(brave_tools, "get_app_config", lambda: _config())

    result = json.loads(brave_tools.web_search_tool.invoke({"query": "example"}))

    assert result["error"] == "BRAVE_SEARCH_API_KEY is not configured"
    assert result["query"] == "example"


def test_brave_search_uses_config_and_returns_citations(monkeypatch):
    captured = {}

    def fake_get(self, url, *, headers, params):
        captured["url"] = url
        captured["headers"] = headers
        captured["params"] = params
        return httpx.Response(
            200,
            json={
                "web": {
                    "results": [
                        {
                            "title": "Brave result",
                            "url": "https://example.com/brave",
                            "description": "Brave evidence.",
                        }
                    ]
                }
            },
            request=httpx.Request("GET", url),
        )

    monkeypatch.delenv("BRAVE_SEARCH_API_KEY", raising=False)
    monkeypatch.setattr(
        brave_tools,
        "get_app_config",
        lambda: _config({"api_key": "config-key", "max_results": 99}),
    )
    monkeypatch.setattr(httpx.Client, "get", fake_get)

    result = json.loads(brave_tools.web_search_tool.invoke({"query": "example"}))

    assert captured["url"] == brave_tools._BRAVE_ENDPOINT
    assert captured["headers"]["X-Subscription-Token"] == "config-key"
    assert captured["params"] == {"q": "example", "count": 20, "text_decorations": False}
    assert result["query"] == "example"
    assert result["total_results"] == 1
    item = result["results"][0]
    assert item["title"] == "Brave result"
    assert item["url"] == "https://example.com/brave"
    assert item["content"] == "Brave evidence."
    assert item["citationUrl"] == "https://example.com/brave"
    assert item["citationProvider"] == "brave"
    assert item["evidenceSnippet"] == "Brave evidence."
