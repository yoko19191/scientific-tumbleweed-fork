"""Built-in academic data search workspace app definition."""

from __future__ import annotations

from deerflow.apps.registry import list_apps, register_app
from deerflow.apps.types import AppDefinition, AppLaunch

APP_ID = "research-data-search"


def register_research_data_search_app() -> AppDefinition:
    """Register the academic data search app once and return its definition."""
    existing = next((app for app in list_apps() if app.id == APP_ID), None)
    if existing is not None:
        return existing

    return register_app(
        AppDefinition(
            id=APP_ID,
            title="学术数据搜索",
            description="集中检索论文、专利、机构和期刊数据，快速查看结果详情与推荐线索。",
            category="科研工具",
            icon="search",
            featured=True,
            tags=("论文", "专利", "机构", "期刊"),
            meta="论文 / 专利 / 机构 / 期刊",
            launch=AppLaunch(href="/workspace/apps/research-data-search"),
        )
    )
