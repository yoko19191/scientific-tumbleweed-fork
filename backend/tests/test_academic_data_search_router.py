import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.gateway import authz
from app.gateway.academic_data_search_service import AcademicDataSearchError
from app.gateway.authz import AuthContext
from app.gateway.routers import academic_data_search as router
from app.gateway.schemas.academic_data_search import (
    PaperSearchRequest,
    PaperSearchResponse,
    SearchMeta,
)


def _request():
    return SimpleNamespace(state=SimpleNamespace())


async def _authenticated(_request):
    return AuthContext(user=object())


async def _anonymous(_request):
    return AuthContext(user=None)


class FakeService:
    def status(self):
        return SimpleNamespace(status="available", configured=True, message="ok", capabilities=[])

    async def search_papers(self, _payload):
        return PaperSearchResponse(meta=SearchMeta(page=1, page_size=10, total=0), items=[])


class ErrorService:
    async def search_papers(self, _payload):
        raise AcademicDataSearchError("timeout", "数据服务响应超时，请稍后重试。", 504)


def test_status_requires_authenticated_user(monkeypatch):
    monkeypatch.setattr(authz, "_authenticate", _anonymous)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(router.get_status(request=_request(), service=FakeService()))

    assert exc.value.status_code == 401


def test_search_papers_requires_authenticated_user(monkeypatch):
    monkeypatch.setattr(authz, "_authenticate", _anonymous)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            router.search_papers(
                payload=PaperSearchRequest(query="agent"),
                request=_request(),
                service=FakeService(),
            )
        )

    assert exc.value.status_code == 401


def test_search_papers_returns_normalized_response(monkeypatch):
    monkeypatch.setattr(authz, "_authenticate", _authenticated)

    response = asyncio.run(
        router.search_papers(
            payload=PaperSearchRequest(query="agent"),
            request=_request(),
            service=FakeService(),
        )
    )

    assert response.meta.total == 0
    assert response.items == []


def test_router_maps_service_errors(monkeypatch):
    monkeypatch.setattr(authz, "_authenticate", _authenticated)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            router.search_papers(
                payload=PaperSearchRequest(query="agent"),
                request=_request(),
                service=ErrorService(),
            )
        )

    assert exc.value.status_code == 504
    assert exc.value.detail == {"code": "timeout", "message": "数据服务响应超时，请稍后重试。"}
