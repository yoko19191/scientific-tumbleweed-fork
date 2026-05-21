"""Sandbox capacity API."""

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from deerflow.sandbox import get_sandbox_provider

router = APIRouter(prefix="/api", tags=["sandbox"])


class SandboxCapacityResponse(BaseModel):
    enabled: bool
    backend: str
    limit: int | None
    active: int
    warm: int
    total: int
    available: int | None
    saturated: bool


_DISABLED_CAPACITY = SandboxCapacityResponse(
    enabled=False,
    backend="unknown",
    limit=None,
    active=0,
    warm=0,
    total=0,
    available=None,
    saturated=False,
)


@router.get(
    "/sandbox/capacity",
    response_model=SandboxCapacityResponse,
    summary="Get Sandbox Capacity",
)
async def get_sandbox_capacity() -> SandboxCapacityResponse:
    """Return current sandbox capacity if the active provider supports it."""
    provider = get_sandbox_provider()
    get_capacity = getattr(provider, "get_capacity", None)
    if not callable(get_capacity):
        return _DISABLED_CAPACITY

    capacity = get_capacity()
    if not isinstance(capacity, dict):
        return _DISABLED_CAPACITY
    return SandboxCapacityResponse(**_normalize_capacity(capacity))


def _normalize_capacity(capacity: dict[str, Any]) -> dict[str, Any]:
    enabled = bool(capacity.get("enabled", True))
    backend = str(capacity.get("backend") or "unknown")
    limit = capacity.get("limit")
    active = int(capacity.get("active") or 0)
    warm = int(capacity.get("warm") or 0)
    total = int(capacity.get("total") if capacity.get("total") is not None else active + warm)
    available = capacity.get("available")
    if limit is None:
        normalized_limit = None
        normalized_available = None
    else:
        normalized_limit = int(limit)
        normalized_available = int(available) if available is not None else max(normalized_limit - total, 0)
    return {
        "enabled": enabled,
        "backend": backend,
        "limit": normalized_limit,
        "active": active,
        "warm": warm,
        "total": total,
        "available": normalized_available,
        "saturated": bool(capacity.get("saturated", normalized_available == 0 if normalized_available is not None else False)),
    }
