"""Workspace apps API."""

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from app.gateway.authz import require_auth
from deerflow.apps import AppDefinition, AppLaunch
from deerflow.apps import list_apps as list_registered_apps
from deerflow.apps.types import AppLaunchMode, AppStatus

router = APIRouter(prefix="/api", tags=["apps"])


class AppLaunchResponse(BaseModel):
    """Frontend launch metadata for a workspace app."""

    href: str = Field(..., description="Workspace URL to open when launching the app")
    mode: AppLaunchMode = Field(default="chat", description="Preferred chat runtime mode")


class AppResponse(BaseModel):
    """Response model for one registered workspace app."""

    id: str = Field(..., description="Stable app identifier")
    title: str = Field(..., description="Display title")
    description: str = Field(..., description="Short app description")
    category: str = Field(..., description="App category key")
    icon: str = Field(default="layout-grid", description="Icon token understood by the frontend")
    status: AppStatus = Field(default="available", description="available or coming_soon")
    featured: bool = Field(default=False, description="Whether to highlight this app")
    tags: list[str] = Field(default_factory=list, description="Searchable app tags")
    meta: str = Field(default="", description="Small secondary label for the card footer")
    launch: AppLaunchResponse | None = Field(default=None, description="Launch action when the app is available")


class AppsListResponse(BaseModel):
    """Response model for listing workspace apps."""

    apps: list[AppResponse]


def _launch_to_response(launch: AppLaunch | None) -> AppLaunchResponse | None:
    if launch is None:
        return None
    return AppLaunchResponse(href=launch.href, mode=launch.mode)


def _app_to_response(app: AppDefinition) -> AppResponse:
    return AppResponse(
        id=app.id,
        title=app.title,
        description=app.description,
        category=app.category,
        icon=app.icon,
        status=app.status,
        featured=app.featured,
        tags=list(app.tags),
        meta=app.meta,
        launch=_launch_to_response(app.launch),
    )


@router.get(
    "/apps",
    response_model=AppsListResponse,
    summary="List Workspace Apps",
    description="List registered workspace app modules. Empty means no real apps are installed yet.",
)
@require_auth
async def list_apps(request: Request) -> AppsListResponse:
    """List all registered workspace app modules."""
    return AppsListResponse(apps=[_app_to_response(app) for app in list_registered_apps()])
