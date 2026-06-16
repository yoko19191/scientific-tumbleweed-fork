from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import pytest

from deerflow.community.browserless import tools
from deerflow.community.browserless.browserless_client import BrowserlessClient


@pytest.mark.anyio
async def test_browserless_client_posts_content_payload(monkeypatch):
    captured = {}

    async def fake_post(self, url, *, json, headers):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        return httpx.Response(
            200,
            text="<html><body>Rendered</body></html>",
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    client = BrowserlessClient(base_url="http://browserless.local/", token="token", timeout_s=5)
    html = await client.fetch_html(
        url="https://example.com",
        wait_for_event="networkidle",
        wait_for_timeout_ms=100,
        wait_for_selector="main",
        reject_resource_types=["image"],
        reject_request_pattern=["analytics"],
    )

    assert html == "<html><body>Rendered</body></html>"
    assert captured["url"] == "http://browserless.local/content"
    assert captured["json"] == {
        "url": "https://example.com",
        "token": "token",
        "waitForEvent": "networkidle",
        "waitForTimeout": 100,
        "waitForSelector": {"selector": "main", "timeout": 5000},
        "rejectResourceTypes": ["image"],
        "rejectRequestPattern": ["analytics"],
    }
    assert captured["headers"]["Content-Type"] == "application/json"


@pytest.mark.anyio
async def test_browserless_fetch_tool_returns_citation_document(monkeypatch):
    mock_config = MagicMock()
    mock_config.get_tool_config.return_value = SimpleNamespace(
        model_extra={
            "base_url": "http://browserless.local",
            "token": "token",
            "timeout_s": "6",
            "wait_for_event": "networkidle",
            "wait_for_timeout_ms": "100",
            "wait_for_selector": "main",
            "reject_resource_types": "image,font",
            "reject_request_pattern": ["analytics"],
        }
    )
    captured = {}

    async def fake_fetch_html(self, **kwargs):
        captured.update(
            {
                "base_url": self.base_url,
                "token": self.token,
                "timeout_s": self.timeout_s,
                **kwargs,
            }
        )
        return "<html><head><title>Rendered title</title></head><body><main>Hello rendered page</main></body></html>"

    monkeypatch.setattr(tools, "get_app_config", lambda: mock_config)
    monkeypatch.setattr(BrowserlessClient, "fetch_html", fake_fetch_html)

    result = await tools.web_fetch_tool.ainvoke("https://example.com/rendered")

    assert captured["base_url"] == "http://browserless.local"
    assert captured["token"] == "token"
    assert captured["timeout_s"] == 6.0
    assert captured["url"] == "https://example.com/rendered"
    assert captured["wait_for_event"] == "networkidle"
    assert captured["wait_for_timeout_ms"] == 100
    assert captured["wait_for_selector"] == "main"
    assert captured["reject_resource_types"] == ["image", "font"]
    assert captured["reject_request_pattern"] == ["analytics"]
    assert result.startswith("# Rendered title\n\ncitationUrl: https://example.com/rendered")
    assert "citationProvider: browserless" in result
    assert "Hello rendered page" in result


@pytest.mark.anyio
async def test_browserless_fetch_tool_short_circuits_error(monkeypatch):
    mock_config = MagicMock()
    mock_config.get_tool_config.return_value = None

    async def fake_fetch_html(self, **kwargs):
        return "Error: Browserless HTTP 500"

    monkeypatch.setattr(tools, "get_app_config", lambda: mock_config)
    monkeypatch.setattr(BrowserlessClient, "fetch_html", fake_fetch_html)

    result = await tools.web_fetch_tool.ainvoke("https://example.com")

    assert result == "Error: Browserless HTTP 500"
