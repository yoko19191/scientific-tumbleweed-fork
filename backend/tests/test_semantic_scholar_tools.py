"""Unit tests for the Semantic Scholar academic search tool group."""

from __future__ import annotations

import json
import sqlite3
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
import yaml

from deerflow.config.app_config import get_app_config, reset_app_config
from deerflow.community.semantic_scholar.cache import SQLiteTTLCache, build_cache_key
from deerflow.community.semantic_scholar.client import SemanticScholarAPIError, SemanticScholarClient, SemanticScholarSettings


def _write_extensions_config(path):
    path.write_text(json.dumps({"mcpServers": {}, "skills": {}}), encoding="utf-8")


def _make_response(status_code: int, payload: dict | None = None, text: str | None = None):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = payload or {}
    response.text = text or json.dumps(payload or {})
    if status_code >= 400:
        error = MagicMock()
        error.response = response
        response.raise_for_status.side_effect = __import__("httpx").HTTPStatusError("boom", request=MagicMock(), response=response)
    else:
        response.raise_for_status.return_value = None
    return response


class TestSemanticScholarConfig:
    def test_config_loads_academic_search_group_and_tools(self, tmp_path, monkeypatch):
        config_path = tmp_path / "config.yaml"
        extensions_path = tmp_path / "extensions_config.json"
        _write_extensions_config(extensions_path)
        config_path.write_text(
            yaml.safe_dump(
                {
                    "sandbox": {"use": "deerflow.sandbox.local:LocalSandboxProvider"},
                    "models": [
                        {
                            "name": "test-model",
                            "use": "langchain_openai:ChatOpenAI",
                            "model": "gpt-test",
                            "supports_thinking": False,
                            "supports_vision": False,
                        }
                    ],
                    "tool_groups": [{"name": "academic_search"}],
                    "tools": [
                        {
                            "name": "academic_search_papers",
                            "group": "academic_search",
                            "use": "deerflow.community.semantic_scholar.tools:academic_search_papers_tool",
                            "cache_db_path": "cache/test.db",
                            "search_ttl_seconds": 123,
                        },
                        {
                            "name": "academic_get_paper",
                            "group": "academic_search",
                            "use": "deerflow.community.semantic_scholar.tools:academic_get_paper_tool",
                            "references_preview_limit": 7,
                            "citations_preview_limit": 8,
                        },
                        {
                            "name": "academic_recommend_papers",
                            "group": "academic_search",
                            "use": "deerflow.community.semantic_scholar.tools:academic_recommend_papers_tool",
                            "recommend_ttl_seconds": 456,
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )

        monkeypatch.setenv("DEER_FLOW_CONFIG_PATH", str(config_path))
        monkeypatch.setenv("DEER_FLOW_EXTENSIONS_CONFIG_PATH", str(extensions_path))
        reset_app_config()
        try:
            config = get_app_config()
            assert config.get_tool_group_config("academic_search") is not None
            assert config.get_tool_config("academic_search_papers").model_extra["cache_db_path"] == "cache/test.db"
            assert config.get_tool_config("academic_search_papers").model_extra["search_ttl_seconds"] == 123
            assert config.get_tool_config("academic_get_paper").model_extra["references_preview_limit"] == 7
            assert config.get_tool_config("academic_get_paper").model_extra["citations_preview_limit"] == 8
            assert config.get_tool_config("academic_recommend_papers").model_extra["recommend_ttl_seconds"] == 456
        finally:
            reset_app_config()


class TestSQLiteTTLCache:
    def test_cache_miss_then_hit_from_sqlite(self, tmp_path):
        db_path = tmp_path / "academic-cache.db"
        cache = SQLiteTTLCache(str(db_path), hot_max_entries=4)
        key = build_cache_key("tool", "/endpoint", {"query": "test"}, ["paperId"])

        assert cache.get(key) is None
        payload = {"value": 1}
        cache.set(key, "tool", payload, ttl_seconds=60)
        cache._hot_cache.clear()

        assert cache.get(key) == payload

    def test_cache_expires_and_lazy_deletes(self, tmp_path, monkeypatch):
        db_path = tmp_path / "academic-cache.db"
        cache = SQLiteTTLCache(str(db_path), hot_max_entries=4)
        key = build_cache_key("tool", "/endpoint", {"query": "test"}, ["paperId"])

        monkeypatch.setattr("deerflow.community.semantic_scholar.cache.time.time", lambda: 100)
        cache.set(key, "tool", {"value": 1}, ttl_seconds=1)
        cache._hot_cache.clear()

        monkeypatch.setattr("deerflow.community.semantic_scholar.cache.time.time", lambda: 102)
        assert cache.get(key) is None

        conn = sqlite3.connect(db_path)
        try:
            count = conn.execute("SELECT COUNT(*) FROM cache_entries WHERE cache_key = ?", (key,)).fetchone()[0]
        finally:
            conn.close()
        assert count == 0

    def test_hot_cache_hit_skips_sqlite(self, tmp_path, monkeypatch):
        db_path = tmp_path / "academic-cache.db"
        cache = SQLiteTTLCache(str(db_path), hot_max_entries=4)
        key = build_cache_key("tool", "/endpoint", {"query": "test"}, ["paperId"])
        cache.set(key, "tool", {"value": 1}, ttl_seconds=60)

        def fail_connect():
            raise AssertionError("sqlite should not be touched on hot-cache hit")

        monkeypatch.setattr(cache, "_connect", fail_connect)
        assert cache.get(key) == {"value": 1}


class TestSemanticScholarClient:
    def test_client_uses_api_key_and_caches(self, tmp_path):
        cache = SQLiteTTLCache(str(tmp_path / "cache.db"))
        settings = SemanticScholarSettings(api_key="tool-key", cache_db_path=str(tmp_path / "cache.db"))
        client = SemanticScholarClient(settings=settings, cache=cache)

        response = _make_response(
            200,
            {
                "total": 1,
                "data": [
                    {
                        "paperId": "p1",
                        "title": "Paper",
                        "abstract": "Abs",
                        "authors": [{"authorId": "a1", "name": "Author"}],
                        "citationCount": 12,
                    }
                ]
            },
        )
        mock_http_client = MagicMock()
        mock_http_client.request.return_value = response
        mock_http_client.__enter__.return_value = mock_http_client
        mock_http_client.__exit__.return_value = None

        with patch("deerflow.community.semantic_scholar.client.httpx.Client", return_value=mock_http_client):
            first = client.search_papers(query="agent", limit=5)
            second = client.search_papers(query="agent", limit=5)

        assert first["total_results"] == 1
        assert second == first
        headers = mock_http_client.request.call_args.kwargs["headers"]
        assert headers["x-api-key"] == "tool-key"
        assert mock_http_client.request.call_count == 1

    def test_client_retries_retryable_status_codes(self, tmp_path):
        cache = SQLiteTTLCache(str(tmp_path / "cache.db"))
        settings = SemanticScholarSettings(api_key=None, cache_db_path=str(tmp_path / "cache.db"), max_retry_attempts=2)
        client = SemanticScholarClient(settings=settings, cache=cache)

        responses = iter(
            [
                _make_response(429, text="rate limited"),
                _make_response(200, {"total": 1, "data": [{"paperId": "p1", "title": "Recovered"}]}),
            ]
        )
        mock_http_client = MagicMock()
        mock_http_client.request.side_effect = lambda *args, **kwargs: next(responses)
        mock_http_client.__enter__.return_value = mock_http_client
        mock_http_client.__exit__.return_value = None

        with (
            patch("deerflow.community.semantic_scholar.client.httpx.Client", return_value=mock_http_client),
            patch("deerflow.community.semantic_scholar.client.time.sleep"),
            patch("deerflow.community.semantic_scholar.client.random.uniform", return_value=0),
        ):
            result = client.search_papers(query="retry", limit=3)

        assert result["total_results"] == 1
        assert mock_http_client.request.call_count == 2

    def test_client_404_raises_api_error(self, tmp_path):
        cache = SQLiteTTLCache(str(tmp_path / "cache.db"))
        settings = SemanticScholarSettings(api_key=None, cache_db_path=str(tmp_path / "cache.db"), max_retry_attempts=1)
        client = SemanticScholarClient(settings=settings, cache=cache)

        mock_http_client = MagicMock()
        mock_http_client.request.return_value = _make_response(404, text="not found")
        mock_http_client.__enter__.return_value = mock_http_client
        mock_http_client.__exit__.return_value = None

        with patch("deerflow.community.semantic_scholar.client.httpx.Client", return_value=mock_http_client):
            with pytest.raises(SemanticScholarAPIError, match="Paper not found"):
                client.get_paper_details("DOI:10.1000/test")


class TestSemanticScholarTools:
    def test_search_tool_returns_structured_results(self, monkeypatch):
        tool_config = SimpleNamespace(model_extra={"max_results": 11, "cache_db_path": "cache.db"})
        mock_config = MagicMock()
        mock_config.get_tool_config.return_value = tool_config
        monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", "env-key")

        with (
            patch("deerflow.community.semantic_scholar.tools.get_app_config", return_value=mock_config),
            patch("deerflow.community.semantic_scholar.tools.get_sqlite_ttl_cache"),
            patch("deerflow.community.semantic_scholar.tools.SemanticScholarClient") as mock_client_cls,
        ):
            mock_client_cls.return_value.search_papers.return_value = {
                "query_or_seed": "graph rag",
                "total_results": 1,
                "results": [{"paperId": "p1", "abstract": "A"}],
            }

            from deerflow.community.semantic_scholar.tools import academic_search_papers_tool

            result = json.loads(academic_search_papers_tool.invoke({"query": "graph rag"}))

        assert result["total_results"] == 1
        assert result["results"][0]["paperId"] == "p1"
        _, kwargs = mock_client_cls.call_args
        assert kwargs["settings"].api_key == "env-key"
        assert kwargs["settings"].cache_db_path == "cache.db"
        mock_client_cls.return_value.search_papers.assert_called_once_with(
            query="graph rag",
            limit=11,
            min_citation_count=None,
            year=None,
            fields_of_study=None,
            open_access_only=None,
        )

    def test_tool_config_api_key_overrides_environment(self, monkeypatch):
        tool_config = SimpleNamespace(model_extra={"api_key": "config-key", "cache_db_path": "cache.db"})
        mock_config = MagicMock()
        mock_config.get_tool_config.return_value = tool_config
        monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", "env-key")

        with (
            patch("deerflow.community.semantic_scholar.tools.get_app_config", return_value=mock_config),
            patch("deerflow.community.semantic_scholar.tools.get_sqlite_ttl_cache"),
            patch("deerflow.community.semantic_scholar.tools.SemanticScholarClient") as mock_client_cls,
        ):
            mock_client_cls.return_value.get_paper_details.return_value = {
                "paper": {"paperId": "p1"},
                "references_preview": [],
                "citations_preview": [],
            }

            from deerflow.community.semantic_scholar.tools import academic_get_paper_tool

            academic_get_paper_tool.invoke({"paper_id": "p1"})

        _, kwargs = mock_client_cls.call_args
        assert kwargs["settings"].api_key == "config-key"

    def test_detail_tool_returns_not_found_structure(self):
        with patch("deerflow.community.semantic_scholar.tools._build_client") as mock_build_client:
            mock_build_client.return_value.get_paper_details.side_effect = SemanticScholarAPIError(
                "Paper not found",
                status_code=404,
            )

            from deerflow.community.semantic_scholar.tools import academic_get_paper_tool

            result = json.loads(academic_get_paper_tool.invoke({"paper_id": "DOI:10.1000/test"}))

        assert result["paper"] is None
        assert result["references_preview"] == []
        assert result["citations_preview"] == []
        assert result["error"]["status_code"] == 404

    def test_recommend_tool_requires_positive_ids(self):
        from deerflow.community.semantic_scholar.tools import academic_recommend_papers_tool

        result = json.loads(academic_recommend_papers_tool.invoke({"positive_paper_ids": []}))

        assert result["results"] == []
        assert "positive_paper_ids" in result["error"]["message"]
