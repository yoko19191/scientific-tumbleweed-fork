import asyncio

import httpx
import pytest

from app.gateway.academic_data_search_service import (
    AcademicDataSearchError,
    AcademicDataSearchService,
    HttpAcademicDataSearchClient,
)
from app.gateway.schemas.academic_data_search import (
    OrganizationSearchRequest,
    PaperRecommendationRequest,
    PaperSearchRequest,
    PatentSearchRequest,
    VenueSearchRequest,
)


class FakeClient:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    async def post(self, operation, payload):
        self.calls.append((operation, dict(payload)))
        response = self.responses[operation]
        if isinstance(response, Exception):
            raise response
        return response


def test_paper_search_maps_request_and_normalizes_response():
    client = FakeClient(
        {
            "paper_search": {
                "data": {
                    "total": 1,
                    "papers": [
                        {
                            "paper_id": "p-1",
                            "title": "Graph Agents for Science",
                            "authors": [{"name": "Ada"}, {"display_name": "Lin"}],
                            "venue": "Nature Methods",
                            "year": "2026",
                            "n_citation": "128",
                            "doi": "10.0000/example",
                            "pdf_url": "https://example.test/paper.pdf",
                        }
                    ],
                }
            }
        }
    )
    service = AcademicDataSearchService(client)

    response = asyncio.run(service.search_papers(PaperSearchRequest(query="agents", page=2, page_size=5)))

    assert client.calls == [("paper_search", {"title": "agents", "page": 2, "size": 5})]
    assert response.meta.total == 1
    assert response.items[0].id == "p-1"
    assert response.items[0].authors == ["Ada", "Lin"]
    assert response.items[0].citation_bucket == "较高引用"
    assert response.items[0].links.pdf_url == "https://example.test/paper.pdf"


def test_paper_recommendation_maps_signals_and_normalizes_links():
    client = FakeClient(
        {
            "paper_recommendation": {
                "data": {
                    "count": 1,
                    "items": [
                        {
                            "id": "p-2",
                            "title": "Recommended Paper",
                            "authors": ["Mei"],
                            "year": 2024,
                            "abstract": "A compact summary.",
                            "url": "https://example.test/paper",
                        }
                    ],
                }
            }
        }
    )
    service = AcademicDataSearchService(client)

    response = asyncio.run(
        service.recommend_papers(
            PaperRecommendationRequest(
                scholar="Dr. Chen",
                topic="",
                organization="",
                year_start=2020,
                year_end=2026,
                language="en",
            )
        )
    )

    assert client.calls == [
        (
            "paper_recommendation",
            {
                "author_name": "Dr. Chen",
                "start_year": 2020,
                "end_year": 2026,
                "language_sort": "en",
                "size": 10,
            },
        )
    ]
    assert response.meta.total == 1
    assert response.items[0].links.primary_url == "https://example.test/paper"


def test_paper_detail_uses_fallback_id_and_missing_fields_are_stable():
    client = FakeClient({"paper_detail": {"data": {"paper": {"title": "Untyped Detail"}}}})
    service = AcademicDataSearchService(client)

    detail = asyncio.run(service.get_paper_detail("paper-fallback"))

    assert client.calls == [("paper_detail", {"ids": ["paper-fallback"]})]
    assert detail.id == "paper-fallback"
    assert detail.title == "Untyped Detail"
    assert detail.authors == []
    assert detail.keywords == []


def test_patent_search_and_detail_are_normalized():
    client = FakeClient(
        {
            "patent_search": {
                "data": {
                    "total_count": 1,
                    "results": [
                        {
                            "patent_id": "pat-1",
                            "title": "Microscope Patent",
                            "publication_date": "2023-05-01",
                            "application_date": "2021-03-01",
                            "inventors": [{"name": "Bo"}],
                            "applicants": ["Lab A"],
                        }
                    ],
                }
            },
            "patent_detail": {
                "data": {
                    "patent": {
                        "id": "pat-1",
                        "title": {"en": ["Microscope Patent"]},
                        "inventor": ["Bo", "Qin"],
                        "applicant": "Lab A",
                        "abstract": "Optics.",
                        "pub_num": "CN123",
                        "app_num": "APP456",
                    }
                }
            },
        }
    )
    service = AcademicDataSearchService(client)

    search_response = asyncio.run(service.search_patents(PatentSearchRequest(query="microscope")))
    detail = asyncio.run(service.get_patent_detail("pat-1"))

    assert client.calls[0] == ("patent_search", {"query": "microscope", "page": 0, "size": 10})
    assert search_response.items[0].publication_year == 2023
    assert search_response.items[0].application_year == 2021
    assert search_response.items[0].first_inventor == "Bo"
    assert detail.inventors == ["Bo", "Qin"]
    assert detail.publication_number == "CN123"
    assert detail.application_number == "APP456"


def test_organization_and_venue_search_are_normalized():
    client = FakeClient(
        {
            "organization_search": {
                "data": {
                    "items": [
                        {
                            "org_id": "org-1",
                            "standard_name": "Example University",
                            "alias": "EU;Example U",
                            "paper_count": "42",
                        }
                    ]
                }
            },
            "venue_search": {
                "data": {
                    "venues": [
                        {
                            "venue_id": "v-1",
                            "english_name": "Journal of Tests",
                            "chinese_name": "测试学报",
                            "type": "journal",
                            "aliases": ["J Tests"],
                        }
                    ]
                }
            },
        }
    )
    service = AcademicDataSearchService(client)

    organizations = asyncio.run(service.search_organizations(OrganizationSearchRequest(query="example")))
    venues = asyncio.run(service.search_venues(VenueSearchRequest(query="journal")))

    assert client.calls == [
        ("organization_search", {"orgs": ["example"], "page": 1, "size": 10}),
        ("venue_search", {"name": "journal", "page": 1, "size": 10}),
    ]
    assert organizations.items[0].aliases == ["EU", "Example U"]
    assert organizations.items[0].total_count == 42
    assert venues.items[0].chinese_name == "测试学报"
    assert venues.items[0].venue_type == "journal"


def test_recommendation_requires_at_least_one_signal():
    with pytest.raises(ValueError, match="scholar, organization, or topic"):
        PaperRecommendationRequest()


def test_http_client_reports_missing_configuration(monkeypatch):
    monkeypatch.delenv("ACADEMIC_DATA_SEARCH_BASE_URL", raising=False)
    monkeypatch.delenv("ACADEMIC_DATA_SEARCH_API_KEY", raising=False)
    monkeypatch.delenv("ACADEMIC_DATA_SEARCH_TOKEN", raising=False)
    monkeypatch.delenv("ACADEMIC_DATA_SEARCH_AUTH_TOKEN", raising=False)
    client = HttpAcademicDataSearchClient()

    with pytest.raises(AcademicDataSearchError) as exc:
        asyncio.run(client.post("paper_search", {"query": "x"}))

    assert exc.value.code == "not_configured"
    assert exc.value.status_code == 503


def test_http_client_normalizes_rate_limit(monkeypatch):
    request = httpx.Request("POST", "https://example.test/search")
    response = httpx.Response(429, request=request)

    class RaisingClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return False

        async def request(self, *args, **kwargs):
            raise httpx.HTTPStatusError("too many", request=request, response=response)

    monkeypatch.setenv("ACADEMIC_DATA_SEARCH_BASE_URL", "https://example.test")
    monkeypatch.setenv("ACADEMIC_DATA_SEARCH_TOKEN", "secret")
    monkeypatch.setattr(httpx, "AsyncClient", lambda *args, **kwargs: RaisingClient())

    with pytest.raises(AcademicDataSearchError) as exc:
        asyncio.run(HttpAcademicDataSearchClient().post("paper_search", {"query": "x"}))

    assert exc.value.code == "rate_limited"
    assert exc.value.status_code == 429


def test_http_client_normalizes_timeout(monkeypatch):
    request = httpx.Request("POST", "https://example.test/search")

    class TimeoutClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return False

        async def request(self, *args, **kwargs):
            raise httpx.TimeoutException("slow", request=request)

    monkeypatch.setenv("ACADEMIC_DATA_SEARCH_BASE_URL", "https://example.test")
    monkeypatch.setenv("ACADEMIC_DATA_SEARCH_TOKEN", "secret")
    monkeypatch.setattr(httpx, "AsyncClient", lambda *args, **kwargs: TimeoutClient())

    with pytest.raises(AcademicDataSearchError) as exc:
        asyncio.run(HttpAcademicDataSearchClient().post("paper_search", {"query": "x"}))

    assert exc.value.code == "timeout"
    assert exc.value.status_code == 504
