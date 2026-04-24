from __future__ import annotations

import json
from typing import Any

from langchain.tools import tool

from deerflow.config import get_app_config

from .cache import get_sqlite_ttl_cache
from .client import SemanticScholarAPIError, SemanticScholarClient, SemanticScholarSettings, resolve_api_key

DEFAULTS = {
    "timeout_seconds": 20,
    "max_results": 10,
    "cache_db_path": "cache/academic_search.db",
    "cache_hot_max_entries": 256,
    "search_ttl_seconds": 43200,
    "paper_detail_ttl_seconds": 604800,
    "recommend_ttl_seconds": 86400,
    "references_preview_limit": 10,
    "citations_preview_limit": 10,
    "max_retry_attempts": 4,
}


def _get_tool_config(tool_name: str) -> Any:
    return get_app_config().get_tool_config(tool_name)


def _get_config_value(tool_name: str, key: str, default: Any) -> Any:
    config = _get_tool_config(tool_name)
    if config is None:
        return default
    return config.model_extra.get(key, default)


def _build_settings(tool_name: str) -> SemanticScholarSettings:
    return SemanticScholarSettings(
        api_key=resolve_api_key(_get_config_value(tool_name, "api_key", None)),
        timeout_seconds=int(_get_config_value(tool_name, "timeout_seconds", DEFAULTS["timeout_seconds"])),
        cache_db_path=str(_get_config_value(tool_name, "cache_db_path", DEFAULTS["cache_db_path"])),
        cache_hot_max_entries=int(_get_config_value(tool_name, "cache_hot_max_entries", DEFAULTS["cache_hot_max_entries"])),
        search_ttl_seconds=int(_get_config_value(tool_name, "search_ttl_seconds", DEFAULTS["search_ttl_seconds"])),
        paper_detail_ttl_seconds=int(
            _get_config_value(tool_name, "paper_detail_ttl_seconds", DEFAULTS["paper_detail_ttl_seconds"])
        ),
        recommend_ttl_seconds=int(_get_config_value(tool_name, "recommend_ttl_seconds", DEFAULTS["recommend_ttl_seconds"])),
        references_preview_limit=int(
            _get_config_value(tool_name, "references_preview_limit", DEFAULTS["references_preview_limit"])
        ),
        citations_preview_limit=int(
            _get_config_value(tool_name, "citations_preview_limit", DEFAULTS["citations_preview_limit"])
        ),
        max_retry_attempts=int(_get_config_value(tool_name, "max_retry_attempts", DEFAULTS["max_retry_attempts"])),
    )


def _build_client(tool_name: str) -> SemanticScholarClient:
    settings = _build_settings(tool_name)
    cache = get_sqlite_ttl_cache(settings.cache_db_path, hot_max_entries=settings.cache_hot_max_entries)
    return SemanticScholarClient(settings=settings, cache=cache)


def _error_response(message: str, *, status_code: int | None = None, paper_result: bool = False) -> str:
    payload: dict[str, Any] = {
        "error": {
            "message": message,
            "status_code": status_code,
        }
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
    configured_default = int(_get_config_value(tool_name, "max_results", DEFAULTS["max_results"]))
    value = configured_default if limit is None or limit == DEFAULTS["max_results"] else limit
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


@tool("academic_search_papers", parse_docstring=True)
def academic_search_papers_tool(
    query: str,
    limit: int = 10,
    min_citation_count: int | None = None,
    year: int | str | None = None,
    fields_of_study: list[str] | str | None = None,
    open_access_only: bool | None = None,
) -> str:
    """Search academic papers from Semantic Scholar for initial literature discovery.

    Args:
        query: Paper search query.
        limit: Maximum number of papers to return.
        min_citation_count: Optional minimum citation count filter.
        year: Optional publication year filter.
        fields_of_study: Optional field or list of fields of study.
        open_access_only: Whether to prefer open-access papers only.
    """
    try:
        stripped_query = query.strip()
        if not stripped_query:
            raise ValueError("query must not be empty")

        client = _build_client("academic_search_papers")
        result = client.search_papers(
            query=stripped_query,
            limit=_normalize_limit("academic_search_papers", limit),
            min_citation_count=min_citation_count,
            year=year,
            fields_of_study=_normalize_string_list(fields_of_study),
            open_access_only=open_access_only,
        )
        return json.dumps(result, indent=2, ensure_ascii=False)
    except ValueError as exc:
        return _error_response(str(exc))
    except SemanticScholarAPIError as exc:
        return _error_response(str(exc), status_code=exc.status_code)


@tool("academic_get_paper", parse_docstring=True)
def academic_get_paper_tool(paper_id: str) -> str:
    """Fetch rich details for a single academic paper and include a small citation/reference preview.

    Args:
        paper_id: Semantic Scholar paper ID or an external ID prefixed with DOI:, ARXIV:, or CorpusId:.
    """
    try:
        normalized_paper_id = paper_id.strip()
        if not normalized_paper_id:
            raise ValueError("paper_id must not be empty")

        client = _build_client("academic_get_paper")
        result = client.get_paper_details(normalized_paper_id)
        return json.dumps(result, indent=2, ensure_ascii=False)
    except ValueError as exc:
        return _error_response(str(exc), paper_result=True)
    except SemanticScholarAPIError as exc:
        return _error_response(str(exc), status_code=exc.status_code, paper_result=True)


@tool("academic_recommend_papers", parse_docstring=True)
def academic_recommend_papers_tool(
    positive_paper_ids: list[str],
    negative_paper_ids: list[str] | None = None,
    limit: int = 10,
) -> str:
    """Recommend related papers using positive and optional negative seed papers.

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

        client = _build_client("academic_recommend_papers")
        result = client.recommend_papers(
            positive_paper_ids=positive_ids,
            negative_paper_ids=negative_ids,
            limit=_normalize_limit("academic_recommend_papers", limit),
        )
        return json.dumps(result, indent=2, ensure_ascii=False)
    except ValueError as exc:
        return _error_response(str(exc))
    except SemanticScholarAPIError as exc:
        return _error_response(str(exc), status_code=exc.status_code)
