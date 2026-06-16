from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

from deerflow.community.ddg_search import tools


def test_web_search_tool_reads_ddgs_config_and_returns_citations(monkeypatch):
    mock_config = MagicMock()
    mock_config.get_tool_config.return_value = SimpleNamespace(
        model_extra={
            "backend": "duckduckgo",
            "max_results": 2,
            "region": "us-en",
            "safesearch": "off",
        }
    )
    captured = {}

    def fake_search_text(**kwargs):
        captured.update(kwargs)
        return [
            {
                "title": "Example title",
                "href": "https://example.com/source",
                "body": "Example evidence.",
            }
        ]

    monkeypatch.setattr(tools, "get_app_config", lambda: mock_config)
    monkeypatch.setattr(tools, "_search_text", fake_search_text)

    result = json.loads(tools.web_search_tool.invoke({"query": "example"}))

    assert captured == {
        "query": "example",
        "max_results": 2,
        "region": "us-en",
        "safesearch": "off",
        "backend": "duckduckgo",
    }
    assert result["query"] == "example"
    assert result["total_results"] == 1
    item = result["results"][0]
    assert item["title"] == "Example title"
    assert item["url"] == "https://example.com/source"
    assert item["content"] == "Example evidence."
    assert item["citationUrl"] == "https://example.com/source"
    assert item["citationTitle"] == "Example title"
    assert item["citationProvider"] == "ddg"
    assert item["citationType"] == "web_page"
    assert item["evidenceSnippet"] == "Example evidence."


def test_wikipedia_backend_avoids_worldwide_region():
    assert tools._resolve_ddgs_region("protein folding", "wt-wt", "wikipedia") == "us-en"
    assert tools._resolve_ddgs_region("蛋白质折叠", "wt-wt", "wikipedia") == "cn-zh"
    assert tools._resolve_ddgs_region("protein folding", "wt-wt", "duckduckgo") == "wt-wt"
