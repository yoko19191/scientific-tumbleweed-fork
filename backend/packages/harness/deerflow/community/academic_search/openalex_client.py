from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass
from typing import Any, cast
from urllib.parse import quote_plus

import httpx

from deerflow.community.semantic_scholar.cache import SQLiteTTLCache, build_cache_key

logger = logging.getLogger(__name__)

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


@dataclass(slots=True)
class OpenAlexSettings:
    email: str | None = None
    timeout_seconds: int = 20
    cache_db_path: str = "cache/academic_search.db"
    cache_hot_max_entries: int = 256
    search_ttl_seconds: int = 43200
    paper_detail_ttl_seconds: int = 604800
    citation_network_ttl_seconds: int = 86400
    max_retry_attempts: int = 4


class OpenAlexAPIError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class OpenAlexClient:
    BASE_URL = "https://api.openalex.org"

    def __init__(self, settings: OpenAlexSettings, cache: SQLiteTTLCache) -> None:
        self._settings = settings
        self._cache = cache

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Accept": "application/json"}
        if self._settings.email:
            headers["User-Agent"] = f"ScientificTumbleweed/1.0 (mailto:{self._settings.email})"
        return headers

    def _build_params(self, **kwargs: Any) -> dict[str, Any]:
        params = {k: v for k, v in kwargs.items() if v is not None}
        if self._settings.email:
            params["mailto"] = self._settings.email
        return params

    def _request_json(
        self,
        *,
        tool_name: str,
        url: str,
        params: dict[str, Any] | None,
        requested_fields: list[str],
        cache_ttl_seconds: int,
    ) -> Any:
        cache_params = {"url": url, "params": params or {}}
        cache_key = build_cache_key(tool_name, url, cache_params, requested_fields)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        last_error: OpenAlexAPIError | None = None
        attempts = max(1, self._settings.max_retry_attempts)

        for attempt in range(attempts):
            try:
                with httpx.Client(timeout=self._settings.timeout_seconds) as client:
                    response = client.get(url, params=params, headers=self._headers())

                if response.status_code == 404:
                    raise OpenAlexAPIError("Resource not found", status_code=404)

                if response.status_code in RETRYABLE_STATUS_CODES:
                    if attempt == attempts - 1:
                        snippet = response.text[:256] if response.text else "Retry limit reached"
                        raise OpenAlexAPIError(snippet, status_code=response.status_code)
                    self._sleep_before_retry(attempt)
                    continue

                response.raise_for_status()
                payload = response.json()
                return self._cache.set(cache_key, tool_name, payload, cache_ttl_seconds)
            except httpx.HTTPStatusError as exc:
                sc = exc.response.status_code if exc.response is not None else None
                msg = exc.response.text[:256] if exc.response is not None and exc.response.text else str(exc)
                last_error = OpenAlexAPIError(msg, status_code=sc)
                if sc not in RETRYABLE_STATUS_CODES or attempt == attempts - 1:
                    raise last_error
                self._sleep_before_retry(attempt)
            except httpx.RequestError as exc:
                last_error = OpenAlexAPIError(str(exc))
                if attempt == attempts - 1:
                    raise last_error
                self._sleep_before_retry(attempt)

        raise last_error or OpenAlexAPIError("OpenAlex request failed")

    @staticmethod
    def _sleep_before_retry(attempt: int) -> None:
        base = 0.5 * (2**attempt)
        time.sleep(base + random.uniform(0, 0.25))

    # ------------------------------------------------------------------
    # Normalization helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _reconstruct_abstract(inverted_index: dict[str, list[int]] | None) -> str | None:
        if not inverted_index:
            return None
        word_positions: list[tuple[int, str]] = []
        for word, positions in inverted_index.items():
            for pos in positions:
                word_positions.append((pos, word))
        word_positions.sort(key=lambda x: x[0])
        return " ".join(w for _, w in word_positions)

    @staticmethod
    def _format_pages(first_page: str | None, last_page: str | None) -> str | None:
        if first_page and last_page:
            return f"{first_page}--{last_page}"
        return first_page or None

    @staticmethod
    def _get_pdf_url(work: dict[str, Any]) -> str | None:
        primary = work.get("primary_location") or {}
        if primary.get("is_oa") and primary.get("pdf_url"):
            return cast(str, primary["pdf_url"])
        for loc in work.get("locations") or []:
            if loc.get("is_oa") and loc.get("pdf_url"):
                return cast(str, loc["pdf_url"])
        return None

    def _parse_work(self, work: dict[str, Any]) -> dict[str, Any]:
        """Normalize an OpenAlex work to the shared paper dict format."""
        authors: list[str] = []
        for authorship in work.get("authorships") or []:
            author_data = authorship.get("author") or {}
            name = author_data.get("display_name")
            if name:
                authors.append(name)

        venue: str | None = None
        primary_location = work.get("primary_location") or {}
        source = primary_location.get("source")
        if isinstance(source, dict):
            venue = source.get("display_name")

        doi = work.get("doi")
        if isinstance(doi, str) and doi.startswith("https://doi.org/"):
            doi = doi[16:]

        biblio = work.get("biblio") or {}

        openalex_id = work.get("id", "")
        if isinstance(openalex_id, str) and "/" in openalex_id:
            openalex_id = openalex_id.rsplit("/", 1)[-1]

        external_ids: dict[str, Any] = {}
        if doi:
            external_ids["DOI"] = doi
        ids_block = work.get("ids") or {}
        if ids_block.get("openalex"):
            external_ids["OpenAlex"] = ids_block["openalex"]

        return {
            "paperId": openalex_id,
            "title": work.get("display_name") or work.get("title") or "Untitled",
            "abstract": self._reconstruct_abstract(work.get("abstract_inverted_index")),
            "tldr": None,
            "year": work.get("publication_year"),
            "venue": venue,
            "authors": authors,
            "citationCount": work.get("cited_by_count", 0),
            "openAccessPdfUrl": self._get_pdf_url(work),
            "source": "openalex",
            "externalIds": external_ids,
            "doi": doi,
            "volume": biblio.get("volume"),
            "issue": biblio.get("issue"),
            "pages": self._format_pages(biblio.get("first_page"), biblio.get("last_page")),
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def search_papers(
        self,
        *,
        query: str,
        limit: int = 10,
        offset: int = 0,
        year_from: int | None = None,
        year_to: int | None = None,
        venue: str | None = None,
        sort: str | None = None,
    ) -> dict[str, Any]:
        filters: list[str] = []
        if year_from and year_to:
            filters.append(f"publication_year:{year_from}-{year_to}")
        elif year_from:
            filters.append(f"publication_year:>{year_from - 1}")
        elif year_to:
            filters.append(f"publication_year:<{year_to + 1}")
        if venue:
            filters.append(f"primary_location.source.display_name.search:{quote_plus(venue)}")

        api_sort = None
        if sort == "publication_date":
            api_sort = "publication_date:desc"
        elif sort == "citation_count":
            api_sort = "cited_by_count:desc"
        elif sort == "relevance":
            api_sort = "relevance_score:desc"

        per_page = min(200, max(limit, 25))
        page = 1 + (offset // per_page) if per_page > 0 else 1

        params = self._build_params(
            search=query,
            per_page=per_page,
            page=page,
            filter=",".join(filters) if filters else None,
            sort=api_sort,
        )

        payload = self._request_json(
            tool_name="academic_search_papers",
            url=f"{self.BASE_URL}/works",
            params=params,
            requested_fields=["search"],
            cache_ttl_seconds=self._settings.search_ttl_seconds,
        )

        raw_results = payload.get("results") or [] if isinstance(payload, dict) else []
        total = (payload.get("meta") or {}).get("count", 0) if isinstance(payload, dict) else 0

        offset_within_page = offset % per_page
        papers = [self._parse_work(w) for w in raw_results if isinstance(w, dict)]
        papers = papers[offset_within_page:][:limit]

        return {
            "query_or_seed": query,
            "total_results": total,
            "results": papers,
        }

    def get_paper(self, paper_id: str) -> dict[str, Any] | None:
        pid = paper_id.strip()
        if pid.startswith("W"):
            url = f"{self.BASE_URL}/works/{pid}"
        elif pid.startswith("10."):
            url = f"{self.BASE_URL}/works/doi:{pid}"
        elif pid.startswith("https://doi.org/"):
            url = f"{self.BASE_URL}/works/doi:{pid[16:]}"
        else:
            url = f"{self.BASE_URL}/works/{pid}"

        params = self._build_params()

        try:
            payload = self._request_json(
                tool_name="academic_get_paper",
                url=url,
                params=params,
                requested_fields=["detail"],
                cache_ttl_seconds=self._settings.paper_detail_ttl_seconds,
            )
            return self._parse_work(payload) if isinstance(payload, dict) else None
        except OpenAlexAPIError as exc:
            if exc.status_code == 404:
                return None
            raise

    def get_citations(
        self,
        paper_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        paper = self.get_paper(paper_id)
        if not paper:
            return {
                "paper_id": paper_id,
                "citation_count": 0,
                "citing_papers": [],
                "has_more": False,
            }

        openalex_id = paper["paperId"]
        per_page = min(200, max(limit, 25))
        page = 1 + (offset // per_page) if per_page > 0 else 1

        params = self._build_params(
            filter=f"cites:{openalex_id}",
            per_page=per_page,
            page=page,
        )

        try:
            payload = self._request_json(
                tool_name="academic_get_citations",
                url=f"{self.BASE_URL}/works",
                params=params,
                requested_fields=["citations"],
                cache_ttl_seconds=self._settings.paper_detail_ttl_seconds,
            )
            raw = payload.get("results") or [] if isinstance(payload, dict) else []
            total = (payload.get("meta") or {}).get("count", 0) if isinstance(payload, dict) else 0

            offset_within_page = offset % per_page
            citing = [self._parse_work(w) for w in raw if isinstance(w, dict)]
            citing = citing[offset_within_page:][:limit]

            return {
                "paper_id": paper_id,
                "citation_count": paper.get("citationCount", 0),
                "citing_papers": citing,
                "has_more": offset + len(citing) < total,
            }
        except OpenAlexAPIError:
            return {
                "paper_id": paper_id,
                "citation_count": paper.get("citationCount", 0),
                "citing_papers": [],
                "has_more": False,
            }

    def search_by_author(
        self,
        author_name: str,
        limit: int = 20,
        offset: int = 0,
        year_from: int | None = None,
        year_to: int | None = None,
    ) -> dict[str, Any]:
        filters = [f"raw_author_name.search:{quote_plus(author_name)}"]
        if year_from and year_to:
            filters.append(f"publication_year:{year_from}-{year_to}")
        elif year_from:
            filters.append(f"publication_year:>{year_from - 1}")
        elif year_to:
            filters.append(f"publication_year:<{year_to + 1}")

        per_page = min(200, max(limit, 25))
        page = 1 + (offset // per_page) if per_page > 0 else 1

        params = self._build_params(
            filter=",".join(filters),
            per_page=per_page,
            page=page,
            sort="publication_year:desc",
        )

        payload = self._request_json(
            tool_name="academic_search_author",
            url=f"{self.BASE_URL}/works",
            params=params,
            requested_fields=["author_search"],
            cache_ttl_seconds=self._settings.search_ttl_seconds,
        )

        raw = payload.get("results") or [] if isinstance(payload, dict) else []
        total = (payload.get("meta") or {}).get("count", 0) if isinstance(payload, dict) else 0

        offset_within_page = offset % per_page
        papers = [self._parse_work(w) for w in raw if isinstance(w, dict)]
        papers = papers[offset_within_page:][:limit]

        return {
            "query_or_seed": f"author:{author_name}",
            "total_results": total,
            "results": papers,
        }

    def get_citation_network(
        self,
        paper_id: str,
        max_nodes: int = 50,
        direction: str = "both",
    ) -> dict[str, Any]:
        paper = self.get_paper(paper_id)
        if not paper:
            return {
                "center_paper_id": paper_id,
                "nodes": [],
                "edges": [],
                "node_count": 0,
                "edge_count": 0,
            }

        openalex_id = paper["paperId"]
        nodes: list[dict[str, Any]] = [
            {
                "paper_id": openalex_id,
                "title": paper.get("title"),
                "year": paper.get("year"),
                "citation_count": paper.get("citationCount", 0),
                "is_center": True,
            }
        ]
        edges: list[dict[str, Any]] = []
        seen_ids: set[str] = {openalex_id}

        half_budget = max(max_nodes // 2, 5)

        if direction in ("citing", "both"):
            citing_result = self.get_citations(paper_id, limit=half_budget)
            for cp in citing_result.get("citing_papers") or []:
                cid = cp.get("paperId", "")
                if cid and cid not in seen_ids and len(nodes) < max_nodes:
                    seen_ids.add(cid)
                    nodes.append({
                        "paper_id": cid,
                        "title": cp.get("title"),
                        "year": cp.get("year"),
                        "citation_count": cp.get("citationCount", 0),
                        "is_center": False,
                    })
                    edges.append({"source": cid, "target": openalex_id, "relation": "cites"})

        if direction in ("cited", "both"):
            detail = self._get_referenced_works(openalex_id, limit=half_budget)
            for rp in detail:
                rid = rp.get("paperId", "")
                if rid and rid not in seen_ids and len(nodes) < max_nodes:
                    seen_ids.add(rid)
                    nodes.append({
                        "paper_id": rid,
                        "title": rp.get("title"),
                        "year": rp.get("year"),
                        "citation_count": rp.get("citationCount", 0),
                        "is_center": False,
                    })
                    edges.append({"source": openalex_id, "target": rid, "relation": "cites"})

        return {
            "center_paper_id": paper_id,
            "nodes": nodes,
            "edges": edges,
            "node_count": len(nodes),
            "edge_count": len(edges),
        }

    def _get_referenced_works(self, openalex_id: str, limit: int = 25) -> list[dict[str, Any]]:
        """Fetch papers referenced by the given work."""
        params = self._build_params(
            filter=f"cited_by:{openalex_id}",
            per_page=min(limit, 200),
            page=1,
        )
        try:
            payload = self._request_json(
                tool_name="academic_get_citation_network",
                url=f"{self.BASE_URL}/works",
                params=params,
                requested_fields=["referenced"],
                cache_ttl_seconds=self._settings.citation_network_ttl_seconds,
            )
            raw = payload.get("results") or [] if isinstance(payload, dict) else []
            return [self._parse_work(w) for w in raw[:limit] if isinstance(w, dict)]
        except OpenAlexAPIError:
            return []
