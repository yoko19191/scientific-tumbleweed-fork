from __future__ import annotations

import json
import os
from typing import Any

from langchain.tools import tool

from deerflow.community.semantic_scholar.cache import get_sqlite_ttl_cache
from deerflow.community.semantic_scholar.client import (
    SemanticScholarAPIError,
    SemanticScholarClient,
    SemanticScholarSettings,
    resolve_api_key,
)
from deerflow.config import get_app_config

from .aggregator import AcademicAggregator
from .openalex_client import OpenAlexClient, OpenAlexSettings

DEFAULTS = {
    "timeout_seconds": 20,
    "max_results": 10,
    "cache_db_path": "cache/academic_search.db",
    "cache_hot_max_entries": 256,
    "search_ttl_seconds": 43200,
    "paper_detail_ttl_seconds": 604800,
    "recommend_ttl_seconds": 86400,
    "citation_network_ttl_seconds": 86400,
    "references_preview_limit": 10,
    "citations_preview_limit": 10,
    "max_retry_attempts": 4,
}


def _get_config_value(tool_name: str, key: str, default: Any) -> Any:
    config = get_app_config().get_tool_config(tool_name)
    if config is None:
        return default
    return config.model_extra.get(key, default)


def _resolve_openalex_email(tool_name: str) -> str | None:
    val = _get_config_value(tool_name, "openalex_email", None)
    return val or os.getenv("OPENALEX_EMAIL")


def _build_aggregator(tool_name: str) -> AcademicAggregator:
    db_path = str(_get_config_value(tool_name, "cache_db_path", DEFAULTS["cache_db_path"]))
    hot_max = int(_get_config_value(tool_name, "cache_hot_max_entries", DEFAULTS["cache_hot_max_entries"]))
    cache = get_sqlite_ttl_cache(db_path, hot_max_entries=hot_max)

    s2_settings = SemanticScholarSettings(
        api_key=resolve_api_key(_get_config_value(tool_name, "api_key", None)),
        timeout_seconds=int(_get_config_value(tool_name, "timeout_seconds", DEFAULTS["timeout_seconds"])),
        cache_db_path=db_path,
        cache_hot_max_entries=hot_max,
        search_ttl_seconds=int(_get_config_value(tool_name, "search_ttl_seconds", DEFAULTS["search_ttl_seconds"])),
        paper_detail_ttl_seconds=int(
            _get_config_value(tool_name, "paper_detail_ttl_seconds", DEFAULTS["paper_detail_ttl_seconds"])
        ),
        recommend_ttl_seconds=int(
            _get_config_value(tool_name, "recommend_ttl_seconds", DEFAULTS["recommend_ttl_seconds"])
        ),
        references_preview_limit=int(
            _get_config_value(tool_name, "references_preview_limit", DEFAULTS["references_preview_limit"])
        ),
        citations_preview_limit=int(
            _get_config_value(tool_name, "citations_preview_limit", DEFAULTS["citations_preview_limit"])
        ),
        max_retry_attempts=int(_get_config_value(tool_name, "max_retry_attempts", DEFAULTS["max_retry_attempts"])),
    )
    s2_client = SemanticScholarClient(settings=s2_settings, cache=cache)

    oa_settings = OpenAlexSettings(
        email=_resolve_openalex_email(tool_name),
        timeout_seconds=int(_get_config_value(tool_name, "timeout_seconds", DEFAULTS["timeout_seconds"])),
        cache_db_path=db_path,
        cache_hot_max_entries=hot_max,
        search_ttl_seconds=int(_get_config_value(tool_name, "search_ttl_seconds", DEFAULTS["search_ttl_seconds"])),
        paper_detail_ttl_seconds=int(
            _get_config_value(tool_name, "paper_detail_ttl_seconds", DEFAULTS["paper_detail_ttl_seconds"])
        ),
        citation_network_ttl_seconds=int(
            _get_config_value(tool_name, "citation_network_ttl_seconds", DEFAULTS["citation_network_ttl_seconds"])
        ),
        max_retry_attempts=int(_get_config_value(tool_name, "max_retry_attempts", DEFAULTS["max_retry_attempts"])),
    )
    oa_client = OpenAlexClient(settings=oa_settings, cache=cache)

    return AcademicAggregator(openalex=oa_client, s2=s2_client)


def _error_response(message: str, *, status_code: int | None = None, paper_result: bool = False) -> str:
    payload: dict[str, Any] = {
        "error": {"message": message, "status_code": status_code},
    }
    if paper_result:
        payload["paper"] = None
        payload["references_preview"] = []
        payload["citations_preview"] = []
    else:
        payload["query_or_seed"] = None
        payload["total_results"] = 0
        payload["results"] = []
    return json.dumps(payload, indent=2, ensure_ascii=False)


def _normalize_limit(tool_name: str, limit: int | None) -> int:
    configured = int(_get_config_value(tool_name, "max_results", DEFAULTS["max_results"]))
    value = configured if limit is None or limit == DEFAULTS["max_results"] else limit
    if value <= 0:
        raise ValueError("limit must be greater than 0")
    return value


def _normalize_string_list(value: list[str] | str | None) -> list[str] | str | None:
    if isinstance(value, list):
        return [item.strip() for item in value if isinstance(item, str) and item.strip()]
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


# ======================================================================
# Enhanced existing tools
# ======================================================================


@tool("academic_search_papers", parse_docstring=True)
def academic_search_papers_tool(
    query: str,
    limit: int = 10,
    min_citation_count: int | None = None,
    year: int | str | None = None,
    fields_of_study: list[str] | str | None = None,
    open_access_only: bool | None = None,
    source: str = "auto",
    year_from: int | None = None,
    year_to: int | None = None,
    venue: str | None = None,
    sort: str | None = None,
) -> str:
    """Search academic papers across OpenAlex and Semantic Scholar for literature discovery.

    Args:
        query: Paper search query.
        limit: Maximum number of papers to return.
        min_citation_count: Optional minimum citation count filter (S2 only).
        year: Optional publication year filter (e.g. 2024 or "2020-2024").
        fields_of_study: Optional field or list of fields of study (S2 only).
        open_access_only: Whether to prefer open-access papers only (S2 only).
        source: Data source — "auto" (OpenAlex with S2 fallback), "openalex", or "semantic_scholar".
        year_from: Filter papers from this year (inclusive).
        year_to: Filter papers until this year (inclusive).
        venue: Filter by venue/journal name.
        sort: Sort order — "relevance", "publication_date", or "citation_count".
    """
    try:
        stripped = query.strip()
        if not stripped:
            raise ValueError("query must not be empty")

        agg = _build_aggregator("academic_search_papers")
        result = agg.search_papers(
            query=stripped,
            limit=_normalize_limit("academic_search_papers", limit),
            source=source,
            min_citation_count=min_citation_count,
            year=year,
            year_from=year_from,
            year_to=year_to,
            fields_of_study=_normalize_string_list(fields_of_study),
            open_access_only=open_access_only,
            venue=venue,
            sort=sort,
        )
        return json.dumps(result, indent=2, ensure_ascii=False)
    except ValueError as exc:
        return _error_response(str(exc))
    except SemanticScholarAPIError as exc:
        return _error_response(str(exc), status_code=exc.status_code)
    except Exception as exc:
        return _error_response(str(exc))


@tool("academic_get_paper", parse_docstring=True)
def academic_get_paper_tool(paper_id: str) -> str:
    """Fetch rich details for a single academic paper with auto-detection of ID format.

    Supports DOI, arXiv ID, Semantic Scholar ID, and OpenAlex ID. Automatically routes
    to the best data source and falls back to alternatives if the primary source fails.

    Args:
        paper_id: Paper identifier — DOI (10.xxx), arXiv ID (2401.12345), S2 ID (40-char hex), OpenAlex ID (Wxxxx), or prefixed ID (DOI:, ARXIV:, CorpusId:).
    """
    try:
        normalized = paper_id.strip()
        if not normalized:
            raise ValueError("paper_id must not be empty")

        agg = _build_aggregator("academic_get_paper")
        result = agg.get_paper(normalized)
        if result is None:
            return _error_response("Paper not found", status_code=404, paper_result=True)
        return json.dumps({"paper": result}, indent=2, ensure_ascii=False)
    except ValueError as exc:
        return _error_response(str(exc), paper_result=True)
    except SemanticScholarAPIError as exc:
        return _error_response(str(exc), status_code=exc.status_code, paper_result=True)
    except Exception as exc:
        return _error_response(str(exc), paper_result=True)


@tool("academic_recommend_papers", parse_docstring=True)
def academic_recommend_papers_tool(
    positive_paper_ids: list[str],
    negative_paper_ids: list[str] | None = None,
    limit: int = 10,
) -> str:
    """Recommend related papers using positive and optional negative seed papers.

    Uses Semantic Scholar's recommendation engine to discover papers similar to the
    positive seeds and dissimilar to the negative seeds.

    Args:
        positive_paper_ids: Seed paper IDs used to drive recommendations.
        negative_paper_ids: Optional negative paper IDs to steer away from.
        limit: Maximum number of recommendations to return.
    """
    try:
        positive_ids = [item.strip() for item in positive_paper_ids if isinstance(item, str) and item.strip()]
        negative_ids = [item.strip() for item in (negative_paper_ids or []) if isinstance(item, str) and item.strip()]
        if not positive_ids:
            raise ValueError("positive_paper_ids must contain at least one paper id")

        agg = _build_aggregator("academic_recommend_papers")
        result = agg.recommend_papers(
            positive_paper_ids=positive_ids,
            negative_paper_ids=negative_ids,
            limit=_normalize_limit("academic_recommend_papers", limit),
        )
        return json.dumps(result, indent=2, ensure_ascii=False)
    except ValueError as exc:
        return _error_response(str(exc))
    except SemanticScholarAPIError as exc:
        return _error_response(str(exc), status_code=exc.status_code)
    except Exception as exc:
        return _error_response(str(exc))


# ======================================================================
# New tools
# ======================================================================


@tool("academic_get_bibtex", parse_docstring=True)
def academic_get_bibtex_tool(paper_ids: list[str]) -> str:
    """Export BibTeX citations for one or more papers.

    Accepts any paper ID format (DOI, arXiv ID, S2 ID, OpenAlex ID). Generates
    properly formatted BibTeX entries with LaTeX-escaped special characters,
    correct entry types (article/inproceedings/misc), and unique citation keys.

    Args:
        paper_ids: List of paper IDs to export as BibTeX.
    """
    try:
        cleaned = [pid.strip() for pid in paper_ids if isinstance(pid, str) and pid.strip()]
        if not cleaned:
            raise ValueError("paper_ids must contain at least one paper id")

        agg = _build_aggregator("academic_get_bibtex")
        results = agg.get_bibtex_batch(cleaned)

        entries: list[str] = []
        failed: list[str] = []
        for pid in cleaned:
            bib = results.get(pid)
            if bib:
                entries.append(bib)
            else:
                failed.append(pid)

        payload = {
            "bibtex": "\n\n".join(entries) if entries else "",
            "count": len(entries),
            "failed": failed,
        }
        return json.dumps(payload, indent=2, ensure_ascii=False)
    except ValueError as exc:
        return json.dumps({"error": {"message": str(exc)}, "bibtex": "", "count": 0, "failed": []})
    except Exception as exc:
        return json.dumps({"error": {"message": str(exc)}, "bibtex": "", "count": 0, "failed": []})


@tool("academic_search_author", parse_docstring=True)
def academic_search_author_tool(
    author_name: str,
    limit: int = 20,
    year_from: int | None = None,
    year_to: int | None = None,
) -> str:
    """Search papers by author name.

    Finds all papers by a given author, optionally filtered by publication year range.
    Uses OpenAlex as the primary source with Semantic Scholar fallback.

    Args:
        author_name: Author name to search for.
        limit: Maximum number of papers to return.
        year_from: Filter papers from this year (inclusive).
        year_to: Filter papers until this year (inclusive).
    """
    try:
        name = author_name.strip()
        if not name:
            raise ValueError("author_name must not be empty")

        agg = _build_aggregator("academic_search_author")
        result = agg.search_by_author(
            name,
            limit=_normalize_limit("academic_search_author", limit),
            year_from=year_from,
            year_to=year_to,
        )
        return json.dumps(result, indent=2, ensure_ascii=False)
    except ValueError as exc:
        return _error_response(str(exc))
    except Exception as exc:
        return _error_response(str(exc))


@tool("academic_get_citation_network", parse_docstring=True)
def academic_get_citation_network_tool(
    paper_id: str,
    max_nodes: int = 50,
    direction: str = "both",
) -> str:
    """Build a citation network graph around a paper.

    Returns nodes (papers) and edges (citation relationships) for visualization.
    The center paper is always included. Uses OpenAlex citation data.

    Args:
        paper_id: Center paper ID (DOI, arXiv ID, S2 ID, or OpenAlex ID).
        max_nodes: Maximum number of nodes in the network (10-200).
        direction: Citation direction — "citing" (papers that cite this), "cited" (papers this cites), or "both".
    """
    try:
        pid = paper_id.strip()
        if not pid:
            raise ValueError("paper_id must not be empty")

        max_n = max(10, min(200, max_nodes))
        if direction not in ("citing", "cited", "both"):
            direction = "both"

        agg = _build_aggregator("academic_get_citation_network")
        result = agg.get_citation_network(pid, max_nodes=max_n, direction=direction)
        return json.dumps(result, indent=2, ensure_ascii=False)
    except ValueError as exc:
        return json.dumps({"error": {"message": str(exc)}, "nodes": [], "edges": [], "node_count": 0, "edge_count": 0})
    except Exception as exc:
        return json.dumps({"error": {"message": str(exc)}, "nodes": [], "edges": [], "node_count": 0, "edge_count": 0})
