from __future__ import annotations

import os
import random
import threading
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import httpx

from .cache import SQLiteTTLCache, build_cache_key

GRAPH_API_BASE_URL = "https://api.semanticscholar.org/graph/v1"
RECOMMENDATIONS_API_BASE_URL = "https://api.semanticscholar.org/recommendations/v1"
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
ANONYMOUS_MIN_INTERVAL_SECONDS = 0.25

SEARCH_FIELDS = [
    "paperId",
    "title",
    "abstract",
    "tldr",
    "year",
    "venue",
    "authors",
    "citationCount",
    "openAccessPdf",
]

RECOMMEND_FIELDS = [
    "paperId",
    "title",
    "abstract",
    "year",
    "venue",
    "authors",
    "citationCount",
    "openAccessPdf",
]

DETAIL_FIELDS = [
    "paperId",
    "title",
    "abstract",
    "tldr",
    "year",
    "venue",
    "journal",
    "authors",
    "citationCount",
    "referenceCount",
    "openAccessPdf",
    "isOpenAccess",
    "externalIds",
]

RELATION_PREVIEW_FIELDS = [
    "paperId",
    "title",
    "authors",
    "year",
    "citationCount",
]

_ANONYMOUS_LOCK = threading.Lock()
_LAST_ANONYMOUS_REQUEST_AT = 0.0


@dataclass(slots=True)
class SemanticScholarSettings:
    api_key: str | None
    timeout_seconds: int = 20
    cache_db_path: str = "cache/academic_search.db"
    cache_hot_max_entries: int = 256
    search_ttl_seconds: int = 43200
    paper_detail_ttl_seconds: int = 604800
    recommend_ttl_seconds: int = 86400
    references_preview_limit: int = 10
    citations_preview_limit: int = 10
    max_retry_attempts: int = 4


class SemanticScholarAPIError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def resolve_api_key(config_api_key: str | None = None) -> str | None:
    return config_api_key or os.getenv("SEMANTIC_SCHOLAR_API_KEY")


def _coerce_tldr(value: Any) -> str | None:
    if isinstance(value, dict):
        text = value.get("text")
        return text if isinstance(text, str) and text.strip() else None
    if isinstance(value, str) and value.strip():
        return value
    return None


def _normalize_authors(authors: Any) -> list[str]:
    if not isinstance(authors, list):
        return []
    return [a.get("name") for a in authors if isinstance(a, dict) and a.get("name")]


def _normalize_open_access_url(value: Any) -> str | None:
    if isinstance(value, dict):
        url = value.get("url")
        if isinstance(url, str) and url.strip():
            return url.strip()
    return None


def normalize_paper(paper: dict[str, Any], *, include_detail_fields: bool = False) -> dict[str, Any]:
    result: dict[str, Any] = {
        "paperId": paper.get("paperId"),
        "title": paper.get("title"),
        "abstract": paper.get("abstract"),
        "tldr": _coerce_tldr(paper.get("tldr")),
        "year": paper.get("year"),
        "venue": paper.get("venue"),
        "authors": _normalize_authors(paper.get("authors")),
        "citationCount": paper.get("citationCount"),
        "openAccessPdfUrl": _normalize_open_access_url(paper.get("openAccessPdf")),
    }
    if include_detail_fields:
        result["journal"] = paper.get("journal") if isinstance(paper.get("journal"), dict) else None
        result["referenceCount"] = paper.get("referenceCount")
        result["isOpenAccess"] = paper.get("isOpenAccess")
        result["externalIds"] = paper.get("externalIds") or {}
    return result


def normalize_relation_preview(entry: dict[str, Any], paper_key: str) -> dict[str, Any]:
    paper = entry.get(paper_key)
    raw = paper if isinstance(paper, dict) else {}
    return {
        "paperId": raw.get("paperId"),
        "title": raw.get("title"),
        "authors": _normalize_authors(raw.get("authors")),
        "year": raw.get("year"),
        "citationCount": raw.get("citationCount"),
        "isInfluential": entry.get("isInfluential"),
    }


class SemanticScholarClient:
    def __init__(self, settings: SemanticScholarSettings, cache: SQLiteTTLCache) -> None:
        self._settings = settings
        self._cache = cache

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self._settings.api_key:
            headers["x-api-key"] = self._settings.api_key
        return headers

    def _maybe_throttle_anonymous(self) -> None:
        if self._settings.api_key:
            return
        global _LAST_ANONYMOUS_REQUEST_AT
        with _ANONYMOUS_LOCK:
            now = time.monotonic()
            wait_seconds = ANONYMOUS_MIN_INTERVAL_SECONDS - (now - _LAST_ANONYMOUS_REQUEST_AT)
            if wait_seconds > 0:
                time.sleep(wait_seconds)
                now = time.monotonic()
            _LAST_ANONYMOUS_REQUEST_AT = now

    def _request_json(
        self,
        *,
        tool_name: str,
        method: str,
        url: str,
        params: dict[str, Any] | None,
        json_body: dict[str, Any] | None,
        requested_fields: list[str],
        cache_ttl_seconds: int,
    ) -> Any:
        cache_params = {
            "method": method,
            "url": url,
            "params": params or {},
            "json": json_body or {},
        }
        cache_key = build_cache_key(tool_name, url, cache_params, requested_fields)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        last_error: SemanticScholarAPIError | None = None
        attempts = max(1, self._settings.max_retry_attempts)

        for attempt in range(attempts):
            try:
                self._maybe_throttle_anonymous()
                with httpx.Client(timeout=self._settings.timeout_seconds) as client:
                    response = client.request(
                        method,
                        url,
                        params=params,
                        json=json_body,
                        headers=self._headers(),
                    )

                if response.status_code == 404:
                    raise SemanticScholarAPIError("Paper not found", status_code=404)

                if response.status_code in RETRYABLE_STATUS_CODES:
                    if attempt == attempts - 1:
                        body_snippet = response.text[:256] if response.text else "Retry limit reached"
                        raise SemanticScholarAPIError(body_snippet, status_code=response.status_code)
                    self._sleep_before_retry(attempt)
                    continue

                response.raise_for_status()
                payload = response.json()
                return self._cache.set(cache_key, tool_name, payload, cache_ttl_seconds)
            except httpx.HTTPStatusError as exc:
                status_code = exc.response.status_code if exc.response is not None else None
                message = exc.response.text[:256] if exc.response is not None and exc.response.text else str(exc)
                last_error = SemanticScholarAPIError(message, status_code=status_code)
                if status_code not in RETRYABLE_STATUS_CODES or attempt == attempts - 1:
                    raise last_error
                self._sleep_before_retry(attempt)
            except httpx.RequestError as exc:
                last_error = SemanticScholarAPIError(str(exc))
                if attempt == attempts - 1:
                    raise last_error
                self._sleep_before_retry(attempt)

        raise last_error or SemanticScholarAPIError("Semantic Scholar request failed")

    def _sleep_before_retry(self, attempt: int) -> None:
        base = 0.5 * (2**attempt)
        time.sleep(base + random.uniform(0, 0.25))

    def search_papers(
        self,
        *,
        query: str,
        limit: int,
        min_citation_count: int | None = None,
        year: str | int | None = None,
        fields_of_study: list[str] | str | None = None,
        open_access_only: bool | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "query": query,
            "limit": limit,
            "fields": ",".join(SEARCH_FIELDS),
        }
        if min_citation_count is not None:
            params["minCitationCount"] = min_citation_count
        if year is not None:
            params["year"] = year
        if fields_of_study:
            params["fieldsOfStudy"] = ",".join(fields_of_study) if isinstance(fields_of_study, list) else fields_of_study
        if open_access_only is not None:
            params["openAccessPdf"] = open_access_only

        payload = self._request_json(
            tool_name="academic_search_papers",
            method="GET",
            url=f"{GRAPH_API_BASE_URL}/paper/search",
            params=params,
            json_body=None,
            requested_fields=SEARCH_FIELDS,
            cache_ttl_seconds=self._settings.search_ttl_seconds,
        )
        raw_results = payload.get("data") if isinstance(payload, dict) else []
        total = payload.get("total", 0) if isinstance(payload, dict) else 0
        results = [normalize_paper(item) for item in raw_results if isinstance(item, dict)]
        return {
            "query_or_seed": query,
            "total_results": total,
            "results": results,
        }

    def get_paper_details(self, paper_id: str) -> dict[str, Any]:
        encoded_paper_id = quote(paper_id, safe=":")
        paper = self._request_json(
            tool_name="academic_get_paper",
            method="GET",
            url=f"{GRAPH_API_BASE_URL}/paper/{encoded_paper_id}",
            params={"fields": ",".join(DETAIL_FIELDS)},
            json_body=None,
            requested_fields=DETAIL_FIELDS,
            cache_ttl_seconds=self._settings.paper_detail_ttl_seconds,
        )

        references = self._request_json(
            tool_name="academic_get_paper",
            method="GET",
            url=f"{GRAPH_API_BASE_URL}/paper/{encoded_paper_id}/references",
            params={
                "fields": ",".join(RELATION_PREVIEW_FIELDS),
                "limit": self._settings.references_preview_limit,
            },
            json_body=None,
            requested_fields=RELATION_PREVIEW_FIELDS,
            cache_ttl_seconds=self._settings.paper_detail_ttl_seconds,
        )

        citations = self._request_json(
            tool_name="academic_get_paper",
            method="GET",
            url=f"{GRAPH_API_BASE_URL}/paper/{encoded_paper_id}/citations",
            params={
                "fields": ",".join(RELATION_PREVIEW_FIELDS),
                "limit": self._settings.citations_preview_limit,
            },
            json_body=None,
            requested_fields=RELATION_PREVIEW_FIELDS,
            cache_ttl_seconds=self._settings.paper_detail_ttl_seconds,
        )

        reference_results = (references.get("data") or []) if isinstance(references, dict) else []
        citation_results = (citations.get("data") or []) if isinstance(citations, dict) else []
        return {
            "paper": normalize_paper(paper if isinstance(paper, dict) else {}, include_detail_fields=True),
            "references_preview": [
                normalize_relation_preview(item, "citedPaper") for item in reference_results if isinstance(item, dict)
            ],
            "citations_preview": [
                normalize_relation_preview(item, "citingPaper") for item in citation_results if isinstance(item, dict)
            ],
        }

    def recommend_papers(
        self,
        *,
        positive_paper_ids: list[str],
        negative_paper_ids: list[str] | None = None,
        limit: int,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "positivePaperIds": positive_paper_ids,
            "negativePaperIds": negative_paper_ids or [],
        }
        params: dict[str, Any] = {
            "fields": ",".join(RECOMMEND_FIELDS),
            "limit": limit,
        }

        payload = self._request_json(
            tool_name="academic_recommend_papers",
            method="POST",
            url=f"{RECOMMENDATIONS_API_BASE_URL}/papers",
            params=params,
            json_body=body,
            requested_fields=RECOMMEND_FIELDS,
            cache_ttl_seconds=self._settings.recommend_ttl_seconds,
        )
        raw_results = []
        if isinstance(payload, dict):
            if isinstance(payload.get("recommendedPapers"), list):
                raw_results = payload["recommendedPapers"]
            elif isinstance(payload.get("data"), list):
                raw_results = payload["data"]
        results = [normalize_paper(item) for item in raw_results if isinstance(item, dict)]
        return {
            "query_or_seed": {
                "positivePaperIds": positive_paper_ids,
                "negativePaperIds": negative_paper_ids or [],
            },
            "total_results": len(results),
            "results": results,
        }
