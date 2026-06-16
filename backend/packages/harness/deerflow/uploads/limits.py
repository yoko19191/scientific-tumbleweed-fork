"""Upload limit helpers shared by Gateway and embedded client surfaces."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from deerflow.config.app_config import get_app_config

DEFAULT_UPLOAD_MAX_FILES = 10
DEFAULT_UPLOAD_MAX_FILE_SIZE = 50 * 1024 * 1024
DEFAULT_UPLOAD_MAX_TOTAL_SIZE = 100 * 1024 * 1024

_SIZE_RE = re.compile(
    r"^\s*(?P<number>\d+)\s*(?P<unit>b|bytes?|k|kb|kib|m|mb|mib|g|gb|gib)?\s*$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class UploadLimits:
    """App-level upload limits enforced by the Gateway."""

    max_files: int = DEFAULT_UPLOAD_MAX_FILES
    max_file_size: int = DEFAULT_UPLOAD_MAX_FILE_SIZE
    max_total_size: int = DEFAULT_UPLOAD_MAX_TOTAL_SIZE


def _get_uploads_config_value(config: Any, key: str, default: Any) -> Any:
    uploads_cfg = getattr(config, "uploads", None)
    if isinstance(uploads_cfg, dict):
        return uploads_cfg.get(key, default)
    return getattr(uploads_cfg, key, default)


def _parse_size_bytes(value: Any, default: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value if value > 0 else default
    if isinstance(value, str):
        match = _SIZE_RE.fullmatch(value)
        if not match:
            return default
        number = int(match.group("number"))
        unit = (match.group("unit") or "").lower()
        multiplier = {
            "": 1,
            "b": 1,
            "byte": 1,
            "bytes": 1,
            "k": 1024,
            "kb": 1024,
            "kib": 1024,
            "m": 1024 * 1024,
            "mb": 1024 * 1024,
            "mib": 1024 * 1024,
            "g": 1024 * 1024 * 1024,
            "gb": 1024 * 1024 * 1024,
            "gib": 1024 * 1024 * 1024,
        }[unit]
        parsed = number * multiplier
        return parsed if parsed > 0 else default
    return default


def _parse_positive_int(value: Any, default: int) -> int:
    if isinstance(value, bool):
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def get_upload_limits(config: Any | None = None) -> UploadLimits:
    """Return configured app-level upload limits with secure defaults."""

    cfg = config or get_app_config()
    return UploadLimits(
        max_files=_parse_positive_int(
            _get_uploads_config_value(cfg, "max_files", DEFAULT_UPLOAD_MAX_FILES),
            DEFAULT_UPLOAD_MAX_FILES,
        ),
        max_file_size=_parse_size_bytes(
            _get_uploads_config_value(cfg, "max_file_size", DEFAULT_UPLOAD_MAX_FILE_SIZE),
            DEFAULT_UPLOAD_MAX_FILE_SIZE,
        ),
        max_total_size=_parse_size_bytes(
            _get_uploads_config_value(cfg, "max_total_size", DEFAULT_UPLOAD_MAX_TOTAL_SIZE),
            DEFAULT_UPLOAD_MAX_TOTAL_SIZE,
        ),
    )
