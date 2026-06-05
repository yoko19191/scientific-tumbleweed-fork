from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from deerflow.community.academic_search.openalex_client import OpenAlexClient, OpenAlexSettings
from deerflow.community.citations import canonical_web_result
from deerflow.community.semantic_scholar.client import normalize_paper
from deerflow.tools.tools import get_available_tools


class _NoopCache:
    db_path = ":memory:"

    def get(self, cache_key: str):
        return None

    def set(self, cache_key: str, tool_name: str, value, ttl_seconds: int):
        return value


def test_web_citation_fields_preserve_source_fields():
    result = {
        "title": "Example result",
        "url": "https://example.com/source",
        "snippet": "A short source-backed search result.",
        **canonical_web_result(
            title="Example result",
            url="https://example.com/source",
            snippet="A short source-backed search result.",
            provider="tavily",
        ),
    }

    assert result["title"] == "Example result"
    assert result["url"] == "https://example.com/source"
    assert result["snippet"] == "A short source-backed search result."
    assert result["citationUrl"] == "https://example.com/source"
    assert result["citationTitle"] == "Example result"
    assert result["citationProvider"] == "tavily"
    assert result["citationType"] == "web_page"
    assert result["evidenceSnippet"] == "A short source-backed search result."


def test_tavily_search_tool_returns_canonical_citation_fields():
    mock_config = MagicMock()
    mock_config.get_tool_config.return_value = SimpleNamespace(model_extra={"max_results": 3, "api_key": "key"})

    with (
        patch("deerflow.community.tavily.tools.get_app_config", return_value=mock_config),
        patch("deerflow.community.tavily.tools.TavilyClient") as mock_client_cls,
    ):
        mock_client_cls.return_value.search.return_value = {
            "results": [
                {
                    "title": "Tavily title",
                    "url": "https://example.com/tavily",
                    "content": "Tavily summary.",
                }
            ]
        }
        from deerflow.community.tavily.tools import web_search_tool

        result = json.loads(web_search_tool.invoke({"query": "citation test"}))

    assert result[0]["title"] == "Tavily title"
    assert result[0]["url"] == "https://example.com/tavily"
    assert result[0]["snippet"] == "Tavily summary."
    assert result[0]["citationUrl"] == "https://example.com/tavily"
    assert result[0]["citationTitle"] == "Tavily title"
    assert result[0]["citationProvider"] == "tavily"
    assert result[0]["evidenceSnippet"] == "Tavily summary."


def test_tavily_fetch_tool_returns_citation_provenance():
    mock_config = MagicMock()
    mock_config.get_tool_config.return_value = SimpleNamespace(model_extra={"api_key": "key"})

    with (
        patch("deerflow.community.tavily.tools.get_app_config", return_value=mock_config),
        patch("deerflow.community.tavily.tools.TavilyClient") as mock_client_cls,
    ):
        mock_client_cls.return_value.extract.return_value = {
            "results": [
                {
                    "title": "Fetched title",
                    "raw_content": "Fetched body",
                }
            ],
            "failed_results": [],
        }
        from deerflow.community.tavily.tools import web_fetch_tool

        result = web_fetch_tool.invoke({"url": "https://example.com/tavily"})

    assert result.startswith("# Fetched title\n\ncitationUrl: https://example.com/tavily")
    assert "citationTitle: Fetched title" in result
    assert "citationProvider: tavily" in result
    assert "fetchedAt: " in result
    assert result.endswith("Fetched body")


def test_web_fetch_config_binds_fetch_tool_when_enabled():
    config = MagicMock()
    config.tools = [
        SimpleNamespace(
            name="web_search",
            group="web",
            use="deerflow.community.tavily.tools:web_search_tool",
        ),
        SimpleNamespace(
            name="web_fetch",
            group="web",
            use="deerflow.community.jina_ai.tools:web_fetch_tool",
        ),
    ]
    config.models = []
    config.skill_evolution.enabled = False
    config.tool_search.enabled = False
    config.acp_agents = {}
    config.sandbox = MagicMock()

    with patch("deerflow.tools.tools.is_host_bash_allowed", return_value=True):
        tools = get_available_tools(groups=["web"], include_mcp=False, app_config=config)

    assert {tool.name for tool in tools} >= {"web_search", "web_fetch"}


def test_openalex_without_doi_uses_openalex_citation_url():
    client = OpenAlexClient(settings=OpenAlexSettings(), cache=_NoopCache())

    paper = client._parse_work(
        {
            "id": "https://openalex.org/W123456",
            "display_name": "OpenAlex Paper",
            "publication_year": 2024,
            "cited_by_count": 9,
            "ids": {"openalex": "https://openalex.org/W123456"},
            "abstract_inverted_index": {"Evidence": [0], "snippet": [1]},
            "primary_location": {"source": {"display_name": "Journal"}},
            "biblio": {},
        }
    )

    assert paper["paperId"] == "W123456"
    assert paper["title"] == "OpenAlex Paper"
    assert paper["citationUrl"] == "https://openalex.org/W123456"
    assert paper["citationTitle"] == "OpenAlex Paper"
    assert paper["citationProvider"] == "openalex"
    assert paper["citationType"] == "academic_paper"
    assert paper["evidenceSnippet"] == "Evidence snippet"
    assert paper["openAccessPdfUrl"] is None


def test_openalex_with_doi_prefers_doi_but_preserves_provider_url():
    client = OpenAlexClient(settings=OpenAlexSettings(), cache=_NoopCache())

    paper = client._parse_work(
        {
            "id": "https://openalex.org/W999",
            "display_name": "DOI Paper",
            "doi": "https://doi.org/10.1234/test",
            "publication_year": 2024,
            "ids": {"openalex": "https://openalex.org/W999"},
            "primary_location": {"is_oa": True, "pdf_url": "https://example.com/paper.pdf"},
            "biblio": {},
        }
    )

    assert paper["citationUrl"] == "https://doi.org/10.1234/test"
    assert paper["doiUrl"] == "https://doi.org/10.1234/test"
    assert paper["providerUrl"] == "https://openalex.org/W999"
    assert paper["openAccessPdfUrl"] == "https://example.com/paper.pdf"


def test_semantic_scholar_paper_uses_semantic_scholar_citation_url():
    paper_id = "204e3073870fae3d05bcbc2f6a8e263d9b72e776"

    paper = normalize_paper(
        {
            "paperId": paper_id,
            "title": "Attention Is All You Need",
            "abstract": "Transformer evidence.",
            "authors": [{"name": "Ashish Vaswani"}],
            "citationCount": 100,
        }
    )

    assert paper["paperId"] == paper_id
    assert paper["citationUrl"] == f"https://www.semanticscholar.org/paper/{paper_id}"
    assert paper["citationTitle"] == "Attention Is All You Need"
    assert paper["citationProvider"] == "semantic_scholar"
    assert paper["evidenceSnippet"] == "Transformer evidence."


def test_semantic_scholar_detail_with_doi_prefers_doi_url():
    paper_id = "204e3073870fae3d05bcbc2f6a8e263d9b72e776"

    paper = normalize_paper(
        {
            "paperId": paper_id,
            "title": "DOI Detail",
            "externalIds": {"DOI": "10.5555/example"},
            "authors": [],
        },
        include_detail_fields=True,
    )

    assert paper["citationUrl"] == "https://doi.org/10.5555/example"
    assert paper["doiUrl"] == "https://doi.org/10.5555/example"
    assert paper["providerUrl"] == f"https://www.semanticscholar.org/paper/{paper_id}"
    assert paper["externalIds"]["DOI"] == "10.5555/example"


def test_openalex_citation_network_nodes_include_citation_fields(monkeypatch):
    client = OpenAlexClient(settings=OpenAlexSettings(), cache=_NoopCache())

    center = {
        "paperId": "W1",
        "title": "Center",
        "year": 2024,
        "citationCount": 2,
        "citationUrl": "https://openalex.org/W1",
        "citationTitle": "Center",
        "citationProvider": "openalex",
        "citationType": "academic_paper",
        "evidenceSnippet": "Center evidence.",
    }
    citing = {
        "paperId": "W2",
        "title": "Citing",
        "year": 2025,
        "citationCount": 1,
        "citationUrl": "https://openalex.org/W2",
        "citationTitle": "Citing",
        "citationProvider": "openalex",
        "citationType": "academic_paper",
        "evidenceSnippet": "Citing evidence.",
    }

    monkeypatch.setattr(client, "get_paper", lambda paper_id: center)
    monkeypatch.setattr(
        client,
        "get_citations",
        lambda paper_id, limit=20, offset=0: {"citing_papers": [citing]},
    )
    monkeypatch.setattr(client, "_get_referenced_works", lambda openalex_id, limit=25: [])

    network = client.get_citation_network("W1", max_nodes=10, direction="citing")

    assert network["nodes"][0]["citationUrl"] == "https://openalex.org/W1"
    assert network["nodes"][1]["citationUrl"] == "https://openalex.org/W2"
    assert network["nodes"][1]["citationProvider"] == "openalex"
