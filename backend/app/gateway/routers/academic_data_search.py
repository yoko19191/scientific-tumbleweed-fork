"""Gateway API for the academic data search workspace app."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import APIRouter, Depends, HTTPException, Request

from app.gateway.academic_data_search_service import (
    AcademicDataSearchError,
    AcademicDataSearchService,
)
from app.gateway.authz import get_auth_context, require_auth
from app.gateway.schemas.academic_data_search import (
    AcademicDataSearchErrorDetail,
    AcademicDataSearchStatusResponse,
    OrganizationSearchRequest,
    OrganizationSearchResponse,
    PaperDetail,
    PaperRecommendationRequest,
    PaperRecommendationResponse,
    PaperSearchRequest,
    PaperSearchResponse,
    PatentDetail,
    PatentSearchRequest,
    PatentSearchResponse,
    VenueSearchRequest,
    VenueSearchResponse,
)

router = APIRouter(
    prefix="/api/apps/research-data-search",
    tags=["apps"],
)

def get_academic_data_search_service() -> AcademicDataSearchService:
    """Return the academic data search service."""
    return AcademicDataSearchService()


def _require_authenticated_user(request: Request) -> None:
    auth_context = get_auth_context(request)
    if auth_context is None or not auth_context.is_authenticated:
        raise HTTPException(status_code=401, detail="Authentication required")


async def _handle_service_error[T](operation: Callable[[], Awaitable[T]]) -> T:
    try:
        return await operation()
    except AcademicDataSearchError as exc:
        detail = AcademicDataSearchErrorDetail(code=exc.code, message=exc.message)
        raise HTTPException(status_code=exc.status_code, detail=detail.model_dump()) from exc


@router.get(
    "/status",
    response_model=AcademicDataSearchStatusResponse,
    summary="Get academic data search status",
)
@require_auth
async def get_status(
    request: Request,
    service: AcademicDataSearchService = Depends(get_academic_data_search_service),
) -> AcademicDataSearchStatusResponse:
    """Return backend configuration status for the workspace app."""
    _require_authenticated_user(request)
    return service.status()


@router.post(
    "/papers/search",
    response_model=PaperSearchResponse,
    summary="Search papers",
)
@require_auth
async def search_papers(
    payload: PaperSearchRequest,
    request: Request,
    service: AcademicDataSearchService = Depends(get_academic_data_search_service),
) -> PaperSearchResponse:
    """Search papers with normalized response fields."""
    _require_authenticated_user(request)
    return await _handle_service_error(lambda: service.search_papers(payload))


@router.post(
    "/papers/recommendations",
    response_model=PaperRecommendationResponse,
    summary="Recommend papers",
)
@require_auth
async def recommend_papers(
    payload: PaperRecommendationRequest,
    request: Request,
    service: AcademicDataSearchService = Depends(get_academic_data_search_service),
) -> PaperRecommendationResponse:
    """Recommend papers from scholar, organization, or topic signals."""
    _require_authenticated_user(request)
    return await _handle_service_error(lambda: service.recommend_papers(payload))


@router.get(
    "/papers/{paper_id}",
    response_model=PaperDetail,
    summary="Get paper detail",
)
@require_auth
async def get_paper_detail(
    paper_id: str,
    request: Request,
    service: AcademicDataSearchService = Depends(get_academic_data_search_service),
) -> PaperDetail:
    """Get normalized paper detail by record identifier."""
    _require_authenticated_user(request)
    return await _handle_service_error(lambda: service.get_paper_detail(paper_id))


@router.post(
    "/patents/search",
    response_model=PatentSearchResponse,
    summary="Search patents",
)
@require_auth
async def search_patents(
    payload: PatentSearchRequest,
    request: Request,
    service: AcademicDataSearchService = Depends(get_academic_data_search_service),
) -> PatentSearchResponse:
    """Search patents with normalized response fields."""
    _require_authenticated_user(request)
    return await _handle_service_error(lambda: service.search_patents(payload))


@router.get(
    "/patents/{patent_id}",
    response_model=PatentDetail,
    summary="Get patent detail",
)
@require_auth
async def get_patent_detail(
    patent_id: str,
    request: Request,
    service: AcademicDataSearchService = Depends(get_academic_data_search_service),
) -> PatentDetail:
    """Get normalized patent detail by record identifier."""
    _require_authenticated_user(request)
    return await _handle_service_error(lambda: service.get_patent_detail(patent_id))


@router.post(
    "/organizations/search",
    response_model=OrganizationSearchResponse,
    summary="Search organizations",
)
@require_auth
async def search_organizations(
    payload: OrganizationSearchRequest,
    request: Request,
    service: AcademicDataSearchService = Depends(get_academic_data_search_service),
) -> OrganizationSearchResponse:
    """Search organizations with normalized response fields."""
    _require_authenticated_user(request)
    return await _handle_service_error(lambda: service.search_organizations(payload))


@router.post(
    "/venues/search",
    response_model=VenueSearchResponse,
    summary="Search venues",
)
@require_auth
async def search_venues(
    payload: VenueSearchRequest,
    request: Request,
    service: AcademicDataSearchService = Depends(get_academic_data_search_service),
) -> VenueSearchResponse:
    """Search journals or conference venues with normalized response fields."""
    _require_authenticated_user(request)
    return await _handle_service_error(lambda: service.search_venues(payload))
