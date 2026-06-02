"""Upload configuration API."""

from __future__ import annotations

import os
import re
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel, Field


router = APIRouter(prefix="/api/uploads", tags=["uploads"])

_UPLOAD_LOCATION_MARKER = "location ~ ^/api/threads/[^/]+/uploads"
_CLIENT_MAX_BODY_SIZE_RE = re.compile(
    r"(?m)^\s*client_max_body_size\s+([^;]+);"
)


class UploadConfigResponse(BaseModel):
    """Upload limits reflected from nginx configuration."""

    max_body_bytes: int | None = Field(
        default=None,
        description="Maximum upload request body size in bytes. Null means nginx limit is disabled or unknown.",
    )
    max_body_size: str | None = Field(
        default=None,
        description="Original nginx client_max_body_size value.",
    )


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _nginx_config_candidates() -> tuple[Path, ...]:
    configured = os.getenv("DEER_FLOW_NGINX_CONFIG_PATH")
    candidates: list[Path] = []
    if configured:
        candidates.append(Path(configured).expanduser())

    root = _repo_root()
    candidates.extend(
        [
            root / "docker" / "nginx" / "nginx.local.conf",
            root / "docker" / "nginx" / "nginx.conf",
        ]
    )
    return tuple(dict.fromkeys(path.resolve() for path in candidates))


def _parse_nginx_size(value: str) -> int | None:
    size = value.strip()
    if not size:
        return None

    match = re.fullmatch(r"(?P<number>\d+)(?P<unit>[kKmMgG])?", size)
    if not match:
        return None

    number = int(match.group("number"))
    if number == 0:
        return None

    unit = (match.group("unit") or "").lower()
    multiplier = {
        "": 1,
        "k": 1024,
        "m": 1024 * 1024,
        "g": 1024 * 1024 * 1024,
    }[unit]
    return number * multiplier


def _extract_block(content: str, marker: str) -> str | None:
    marker_index = content.find(marker)
    if marker_index == -1:
        return None

    start = content.find("{", marker_index)
    if start == -1:
        return None

    depth = 0
    for index in range(start, len(content)):
        char = content[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return content[start + 1 : index]
    return None


def _find_client_max_body_size(content: str) -> str | None:
    upload_block = _extract_block(content, _UPLOAD_LOCATION_MARKER)
    if upload_block:
        match = _CLIENT_MAX_BODY_SIZE_RE.search(upload_block)
        if match:
            return match.group(1).strip()

    match = _CLIENT_MAX_BODY_SIZE_RE.search(content)
    if match:
        return match.group(1).strip()
    return None


def _read_upload_limit() -> UploadConfigResponse:
    for path in _nginx_config_candidates():
        try:
            content = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            continue
        except OSError:
            continue

        raw_size = _find_client_max_body_size(content)
        if raw_size is None:
            continue

        return UploadConfigResponse(
            max_body_bytes=_parse_nginx_size(raw_size),
            max_body_size=raw_size,
        )

    return UploadConfigResponse()


@router.get(
    "/config",
    response_model=UploadConfigResponse,
    summary="Get Upload Configuration",
)
async def get_upload_config() -> UploadConfigResponse:
    """Return upload limits derived from nginx configuration."""
    return _read_upload_limit()
