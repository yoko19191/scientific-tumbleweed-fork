"""Backend-only service for academic data search.

The service owns upstream credentials, request mapping, response normalization,
and error translation so the frontend only sees project DTOs.
"""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from app.gateway.schemas.academic_data_search import (
    AcademicDataSearchStatusResponse,
    AcademicLinks,
    OrganizationSearchRequest,
    OrganizationSearchResponse,
    OrganizationSummary,
    PaperDetail,
    PaperRecommendationRequest,
    PaperRecommendationResponse,
    PaperSearchRequest,
    PaperSearchResponse,
    PaperSummary,
    PatentDetail,
    PatentSearchRequest,
    PatentSearchResponse,
    PatentSummary,
    SearchMeta,
    VenueSearchRequest,
    VenueSearchResponse,
    VenueSummary,
)


class AcademicDataSearchError(Exception):
    """Normalized service error."""

    def __init__(self, code: str, message: str, status_code: int = 503) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True)
class AcademicDataSearchConfig:
    """Backend-private upstream configuration."""

    base_url: str
    auth_token: str
    api_key: str | None = None
    platform: str | None = None
    timeout_seconds: float = 12.0

    @classmethod
    def from_env(cls) -> AcademicDataSearchConfig | None:
        base_url = os.getenv("ACADEMIC_DATA_SEARCH_BASE_URL", "").strip()
        api_key = os.getenv("ACADEMIC_DATA_SEARCH_API_KEY", "").strip() or None
        auth_token = (
            os.getenv("ACADEMIC_DATA_SEARCH_TOKEN", "").strip()
            or os.getenv("ACADEMIC_DATA_SEARCH_AUTH_TOKEN", "").strip()
            or (api_key or "")
        )
        platform = os.getenv("ACADEMIC_DATA_SEARCH_PLATFORM", "").strip() or None
        if not base_url or not auth_token:
            return None

        timeout_raw = os.getenv("ACADEMIC_DATA_SEARCH_TIMEOUT_SECONDS", "12").strip()
        try:
            timeout_seconds = max(1.0, float(timeout_raw))
        except ValueError:
            timeout_seconds = 12.0

        return cls(
            base_url=base_url.rstrip("/"),
            auth_token=auth_token,
            api_key=api_key,
            platform=platform,
            timeout_seconds=timeout_seconds,
        )


class AcademicDataSearchClient(Protocol):
    """Backend-only client protocol used by the service and tests."""

    async def post(self, operation: str, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        """Call one configured upstream operation."""


class HttpAcademicDataSearchClient:
    """HTTP implementation for the backend-only academic data provider."""

    _OPERATIONS: dict[str, tuple[str, str]] = {
        "paper_search": ("GET", "/api/paper/search"),
        "paper_recommendation": ("POST", "/api/paper/rec5"),
        "paper_detail": ("POST", "/api/paper/info"),
        "patent_search": ("POST", "/api/patent/search"),
        "patent_detail": ("GET", "/api/patent/info"),
        "organization_search": ("POST", "/api/organization/search"),
        "venue_search": ("POST", "/api/venue/search"),
    }

    def __init__(self, config: AcademicDataSearchConfig | None = None) -> None:
        self._config = config

    async def post(self, operation: str, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        config = self._config or AcademicDataSearchConfig.from_env()
        if config is None:
            raise AcademicDataSearchError(
                code="not_configured",
                message="数据服务尚未配置，请联系管理员完成后端配置。",
                status_code=503,
            )

        method, path = self._OPERATIONS[operation]
        headers = _build_headers(config, method)
        try:
            async with httpx.AsyncClient(base_url=config.base_url, timeout=config.timeout_seconds) as client:
                response = await client.request(
                    method,
                    path,
                    params=dict(payload) if method == "GET" else None,
                    json=dict(payload) if method == "POST" else None,
                    headers=headers,
                )
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise AcademicDataSearchError(
                code="timeout",
                message="数据服务响应超时，请稍后重试。",
                status_code=504,
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise _map_http_status_error(exc) from exc
        except httpx.HTTPError as exc:
            raise AcademicDataSearchError(
                code="service_unavailable",
                message="数据服务暂时不可用，请稍后重试。",
                status_code=503,
            ) from exc

        data = response.json()
        if not isinstance(data, Mapping):
            raise AcademicDataSearchError(
                code="invalid_response",
                message="数据服务返回格式异常，请稍后重试。",
                status_code=502,
            )
        return data


def _build_headers(config: AcademicDataSearchConfig, method: str) -> dict[str, str]:
    headers = {"Authorization": config.auth_token}
    if config.platform:
        headers["X-Platform"] = config.platform
    if method == "POST":
        headers["Content-Type"] = "application/json;charset=utf-8"
    return headers


class AcademicDataSearchService:
    """Application service for normalized academic data search."""

    def __init__(self, client: AcademicDataSearchClient | None = None) -> None:
        self._client = client or HttpAcademicDataSearchClient()

    def status(self) -> AcademicDataSearchStatusResponse:
        configured = AcademicDataSearchConfig.from_env() is not None
        return AcademicDataSearchStatusResponse(
            status="available" if configured else "not_configured",
            configured=configured,
            message="数据服务可用。" if configured else "数据服务尚未配置，查询时会显示可处理的错误状态。",
            capabilities=["论文检索", "论文推荐", "专利检索", "机构检索", "期刊检索"],
        )

    async def search_papers(self, request: PaperSearchRequest) -> PaperSearchResponse:
        payload = {"title": request.query, "page": request.page, "size": request.page_size}
        data = await self._client.post("paper_search", payload)
        return PaperSearchResponse(
            meta=_search_meta(data, request.page, request.page_size),
            items=[_normalize_paper(item) for item in _extract_items(data, "papers", "items", "results")],
        )

    async def recommend_papers(self, request: PaperRecommendationRequest) -> PaperRecommendationResponse:
        payload = {
            "author_name": request.scholar.strip() or None,
            "author_org": request.organization.strip() or None,
            "topics": [request.topic.strip()] if request.topic.strip() else None,
            "start_year": request.year_start,
            "end_year": request.year_end,
            "language_sort": None if request.language == "any" else request.language,
            "size": request.page_size,
        }
        data = await self._client.post(
            "paper_recommendation",
            {key: value for key, value in payload.items() if value is not None},
        )
        return PaperRecommendationResponse(
            meta=_search_meta(data, request.page, request.page_size),
            items=[_normalize_paper(item) for item in _extract_items(data, "papers", "items", "results")],
        )

    async def get_paper_detail(self, paper_id: str) -> PaperDetail:
        data = await self._client.post("paper_detail", {"ids": [paper_id]})
        item = _extract_record(data)
        return _normalize_paper_detail(item, fallback_id=paper_id)

    async def search_patents(self, request: PatentSearchRequest) -> PatentSearchResponse:
        payload = {"query": request.query, "page": request.page - 1, "size": request.page_size}
        data = await self._client.post("patent_search", payload)
        return PatentSearchResponse(
            meta=_search_meta(data, request.page, request.page_size),
            items=[_normalize_patent(item) for item in _extract_items(data, "patents", "items", "results")],
        )

    async def get_patent_detail(self, patent_id: str) -> PatentDetail:
        data = await self._client.post("patent_detail", {"id": patent_id})
        item = _extract_record(data)
        return _normalize_patent_detail(item, fallback_id=patent_id)

    async def search_organizations(self, request: OrganizationSearchRequest) -> OrganizationSearchResponse:
        payload = {"orgs": [request.query], "page": request.page, "size": request.page_size}
        data = await self._client.post("organization_search", payload)
        return OrganizationSearchResponse(
            meta=_search_meta(data, request.page, request.page_size),
            items=[
                _normalize_organization(item)
                for item in _extract_items(data, "organizations", "items", "results")
            ],
        )

    async def search_venues(self, request: VenueSearchRequest) -> VenueSearchResponse:
        payload = {"name": request.query, "page": request.page, "size": request.page_size}
        data = await self._client.post("venue_search", payload)
        return VenueSearchResponse(
            meta=_search_meta(data, request.page, request.page_size),
            items=[_normalize_venue(item) for item in _extract_items(data, "venues", "items", "results")],
        )


def _map_http_status_error(exc: httpx.HTTPStatusError) -> AcademicDataSearchError:
    status_code = exc.response.status_code
    if status_code in {400, 422}:
        return AcademicDataSearchError("invalid_request", "检索条件有误，请调整后重试。", 400)
    if status_code in {401, 403}:
        return AcademicDataSearchError("upstream_auth_failed", "数据服务认证失败，请检查后端配置。", 502)
    if status_code == 429:
        return AcademicDataSearchError("rate_limited", "查询过于频繁，请稍后重试。", 429)
    if status_code >= 500:
        return AcademicDataSearchError("service_unavailable", "数据服务暂时不可用，请稍后重试。", 503)
    return AcademicDataSearchError("service_unavailable", "数据服务暂时不可用，请稍后重试。", 503)


def _extract_record(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    data = payload.get("data", payload)
    if isinstance(data, list):
        return next((item for item in data if isinstance(item, Mapping)), {})
    if isinstance(data, Mapping):
        for key in ("item", "record", "paper", "patent", "result"):
            value = data.get(key)
            if isinstance(value, Mapping):
                return value
            if isinstance(value, list):
                return next((item for item in value if isinstance(item, Mapping)), {})
        return data
    return {}


def _extract_items(payload: Mapping[str, Any], *keys: str) -> list[Mapping[str, Any]]:
    data = payload.get("data", payload)
    candidates: list[Any] = [data]
    if isinstance(data, Mapping):
        candidates.extend(data.get(key) for key in keys)
        candidates.extend(data.get(key) for key in ("list", "records"))

    for candidate in candidates:
        if isinstance(candidate, list):
            nested_items: list[Mapping[str, Any]] = []
            for item in candidate:
                if not isinstance(item, Mapping):
                    continue
                for key in (*keys, "list", "records"):
                    value = item.get(key)
                    if isinstance(value, list):
                        nested_items.extend(nested for nested in value if isinstance(nested, Mapping))
            if nested_items:
                return nested_items
            return [item for item in candidate if isinstance(item, Mapping)]
    return []


def _search_meta(payload: Mapping[str, Any], page: int, page_size: int) -> SearchMeta:
    data = payload.get("data", payload)
    total = _first_int(payload, "total", "total_count", "count")
    if isinstance(data, Mapping):
        total = total or _first_int(data, "total", "total_count", "count")
    if total is None and isinstance(data, list):
        for item in data:
            if isinstance(item, Mapping):
                total = _first_int(item, "total", "total_count", "count")
                if total is not None:
                    break
    return SearchMeta(page=page, page_size=page_size, total=total)


def _normalize_paper(item: Mapping[str, Any]) -> PaperSummary:
    citation_count = _first_int(item, "citation_count", "n_citation", "citations")
    authors = _names(item.get("authors"))
    if not authors:
        first_author = _first_str(item, "first_author", "first_author_name")
        authors = [first_author] if first_author else []
    return PaperSummary(
        id=_first_str(item, "id", "paper_id", "paperId", "pid") or "",
        title=_first_str(item, "title", "name") or "未命名论文",
        authors=authors,
        venue=_field_text(item.get("venue")) or _first_str(item, "venue_name", "raw", "publication", "journal", "conference"),
        year=_first_int(item, "year", "pub_year", "publication_year"),
        citation_count=citation_count,
        citation_bucket=_citation_bucket(citation_count) or _first_str(item, "citation_bucket", "n_citation_bucket"),
        doi=_first_str(item, "doi", "DOI"),
        abstract=_first_str(item, "abstract", "abstract_slice", "summary"),
        links=AcademicLinks(
            primary_url=_first_str(item, "url", "link", "paper_url"),
            pdf_url=_first_str(item, "pdf_url", "pdf", "pdfLink"),
        ),
    )


def _normalize_paper_detail(item: Mapping[str, Any], fallback_id: str) -> PaperDetail:
    summary = _normalize_paper(item)
    return PaperDetail(
        **summary.model_dump(exclude={"id"}),
        id=summary.id or fallback_id,
        keywords=_string_list(item.get("keywords") or item.get("tags")),
    )


def _normalize_patent(item: Mapping[str, Any]) -> PatentSummary:
    inventors = _names(item.get("inventors") or item.get("inventor"))
    applicants = _names(item.get("applicants") or item.get("assignees") or item.get("applicant"))
    return PatentSummary(
        id=_first_str(item, "id", "patent_id", "patentId", "publication_number") or "",
        title=_field_text(item.get("title")) or _first_str(item, "title_zh", "name") or "未命名专利",
        publication_year=_first_int(item, "publication_year", "pub_year")
        or _year_from_date(_first_str(item, "publication_date", "pub_date")),
        application_year=_first_int(item, "application_year", "app_year")
        or _year_from_date(_first_str(item, "application_date", "app_date")),
        first_inventor=_first_str(item, "first_inventor") or (inventors[0] if inventors else None),
        applicant=applicants[0] if applicants else _first_str(item, "applicant"),
    )


def _normalize_patent_detail(item: Mapping[str, Any], fallback_id: str) -> PatentDetail:
    summary = _normalize_patent(item)
    inventors = _names(item.get("inventors") or item.get("inventor"))
    applicants = _names(item.get("applicants") or item.get("assignees") or item.get("applicant"))
    return PatentDetail(
        **summary.model_dump(exclude={"id"}),
        id=summary.id or fallback_id,
        abstract=_first_str(item, "abstract", "summary"),
        inventors=inventors,
        applicants=applicants,
        publication_number=_first_str(item, "publication_number", "pub_number", "pub_num"),
        application_number=_first_str(item, "application_number", "app_number", "app_num"),
    )


def _normalize_organization(item: Mapping[str, Any]) -> OrganizationSummary:
    return OrganizationSummary(
        id=_first_str(item, "id", "org_id", "organization_id") or "",
        name=_first_str(item, "name", "org_name", "standard_name", "display_name") or "未命名机构",
        aliases=_string_list(item.get("aliases") or item.get("alias")),
        total_count=_first_int(item, "total_count", "count", "paper_count"),
    )


def _normalize_venue(item: Mapping[str, Any]) -> VenueSummary:
    return VenueSummary(
        id=_first_str(item, "id", "venue_id", "journal_id") or "",
        english_name=_first_str(item, "english_name", "name_en", "name", "display_name") or "Untitled venue",
        chinese_name=_first_str(item, "chinese_name", "name_zh", "zh_name"),
        venue_type=_first_str(item, "type", "venue_type", "category"),
        aliases=_string_list(item.get("aliases") or item.get("alias")),
    )


def _names(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value] if value.strip() else []
    if not isinstance(value, Sequence):
        return []

    names: list[str] = []
    for item in value:
        if isinstance(item, str) and item.strip():
            names.append(item.strip())
        elif isinstance(item, Mapping):
            name = _first_str(item, "name", "display_name", "full_name")
            if name:
                names.append(name)
    return names


def _field_text(value: Any) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text or None
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            text = _field_text(item)
            if text:
                return text
    if isinstance(value, Mapping):
        for key in ("name", "name_en", "en", "zh", "raw", "title"):
            text = _field_text(value.get(key))
            if text:
                return text
    return None


def _string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [part.strip() for part in value.split(";") if part.strip()]
    if isinstance(value, Sequence):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _first_str(item: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = item.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _first_int(item: Mapping[str, Any], *keys: str) -> int | None:
    for key in keys:
        value = item.get(key)
        if value is None or value == "":
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return None


def _year_from_date(value: str | None) -> int | None:
    if not value or len(value) < 4:
        return None
    try:
        return int(value[:4])
    except ValueError:
        return None


def _citation_bucket(count: int | None) -> str | None:
    if count is None:
        return None
    if count >= 1000:
        return "高引用"
    if count >= 100:
        return "较高引用"
    if count >= 10:
        return "稳定引用"
    return "新近或低引用"
