import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.gateway import authz
from app.gateway.authz import AuthContext
from app.gateway.routers import apps as apps_router
from deerflow.apps import AppDefinition, AppLaunch, clear_apps, list_apps, load_builtin_apps, register_app


def _request():
    return SimpleNamespace(state=SimpleNamespace())


def setup_function():
    clear_apps()


def teardown_function():
    clear_apps()


def test_apps_registry_starts_empty():
    assert list_apps() == []


def test_builtin_research_data_search_app_loader_registers_single_app():
    load_builtin_apps()
    load_builtin_apps()

    matching_apps = [app for app in list_apps() if app.id == "research-data-search"]
    assert len(matching_apps) == 1

    app = matching_apps[0]
    assert app.title == "学术数据搜索"
    assert app.category == "科研工具"
    assert app.launch is not None
    assert app.launch.href == "/workspace/apps/research-data-search"


def test_register_app_returns_sorted_apps():
    register_app(
        AppDefinition(
            id="z-app",
            title="Z App",
            description="Second app",
            category="analysis",
            launch=AppLaunch(href="/workspace/chats/new?app=z-app"),
        )
    )
    register_app(
        AppDefinition(
            id="a-app",
            title="A App",
            description="First app",
            category="writing",
            launch=AppLaunch(href="/workspace/chats/new?app=a-app"),
        )
    )

    assert [app.id for app in list_apps()] == ["a-app", "z-app"]


def test_register_app_rejects_duplicate_ids():
    app = AppDefinition(
        id="duplicate",
        title="Duplicate",
        description="A duplicate app",
        category="analysis",
    )
    register_app(app)

    with pytest.raises(ValueError, match="already registered"):
        register_app(app)


def test_apps_router_requires_authenticated_request(monkeypatch):
    async def reject(_request):
        raise HTTPException(status_code=401, detail="Authentication required")

    monkeypatch.setattr(authz, "_authenticate", reject)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(apps_router.list_apps(request=_request()))

    assert exc.value.status_code == 401


def test_apps_router_lists_registered_apps(monkeypatch):
    async def authenticate(request):
        return AuthContext(user=object())

    monkeypatch.setattr(authz, "_authenticate", authenticate)

    register_app(
        AppDefinition(
            id="real-app",
            title="Real App",
            description="A registered app module",
            category="analysis",
            icon="flask",
            featured=True,
            tags=("rna-seq", "review"),
            meta="Registered module",
            launch=AppLaunch(
                href="/workspace/chats/new?app=real-app",
                mode="computer",
            ),
        )
    )

    response = asyncio.run(apps_router.list_apps(request=_request()))

    apps_by_id = {app.id: app for app in response.apps}
    assert set(apps_by_id) == {"real-app", "research-data-search"}

    app = apps_by_id["real-app"]
    assert app.id == "real-app"
    assert app.featured is True
    assert app.tags == ["rna-seq", "review"]
    assert app.launch is not None
    assert app.launch.href == "/workspace/chats/new?app=real-app"
    assert app.launch.mode == "computer"

    research_app = apps_by_id["research-data-search"]
    assert research_app.title == "学术数据搜索"
    assert research_app.launch is not None
    assert research_app.launch.href == "/workspace/apps/research-data-search"
