"""OpenDAL operator factory + object-key helpers.

Single entry point: :func:`get_operator` / :func:`get_async_operator`.
All persistent IO in the application goes through an ``Operator`` /
``AsyncOperator`` returned from here, **not** through raw ``Path.read_*``
/ ``Path.write_*`` calls.

Backends are selected by :mod:`deerflow.config.storage_config`. The
default is a local-filesystem backend rooted at ``.deer-flow/storage``
so development works out of the box; switching to MinIO later is a
config change, not a code change.

Object key convention
---------------------

Keys use forward slashes and never start with one. ``paths.py`` in this
package centralises the naming patterns (``uploads/<uid>/<tid>/...``,
``outputs/...``, etc.) — callers should prefer those helpers over
hand-formatted strings.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import TYPE_CHECKING

from deerflow.config.storage_config import StorageConfig, get_storage_config

if TYPE_CHECKING:
    import opendal

logger = logging.getLogger(__name__)

_sync_operator: opendal.Operator | None = None
_async_operator: opendal.AsyncOperator | None = None
_operator_lock = threading.Lock()


def _resolve_fs_root(root: str) -> str:
    """Turn a possibly-relative FS root into an absolute path."""
    p = Path(root)
    if not p.is_absolute():
        p = Path.cwd() / p
    p.mkdir(parents=True, exist_ok=True)
    return str(p)


def _build_operator_kwargs(config: StorageConfig) -> tuple[str, dict[str, str]]:
    """Return ``(scheme, kwargs)`` for an OpenDAL operator from config."""
    if config.backend == "fs":
        return "fs", {"root": _resolve_fs_root(config.fs.root)}
    if config.backend == "s3":
        if config.s3 is None:
            raise RuntimeError(
                "storage.backend is 's3' but storage.s3 is missing from config.yaml"
            )
        kwargs: dict[str, str] = {
            "endpoint": config.s3.endpoint,
            "bucket": config.s3.bucket,
            "region": config.s3.region,
            "root": config.s3.root,
        }
        if config.s3.access_key_id:
            kwargs["access_key_id"] = config.s3.access_key_id
        if config.s3.secret_access_key:
            kwargs["secret_access_key"] = config.s3.secret_access_key
        return "s3", kwargs
    raise RuntimeError(f"Unsupported storage backend: {config.backend!r}")


def _make_operators() -> tuple[opendal.Operator, opendal.AsyncOperator]:
    import opendal

    config = get_storage_config()
    scheme, kwargs = _build_operator_kwargs(config)
    logger.info(
        "OpenDAL operators initialising (scheme=%s, root=%s, bucket=%s)",
        scheme,
        kwargs.get("root", ""),
        kwargs.get("bucket", ""),
    )
    return opendal.Operator(scheme, **kwargs), opendal.AsyncOperator(scheme, **kwargs)


def get_operator() -> opendal.Operator:
    """Return the sync :class:`opendal.Operator`, creating it on first call."""
    global _sync_operator, _async_operator
    if _sync_operator is not None:
        return _sync_operator
    with _operator_lock:
        if _sync_operator is None:
            _sync_operator, _async_operator = _make_operators()
    return _sync_operator


def get_async_operator() -> opendal.AsyncOperator:
    """Return the async :class:`opendal.AsyncOperator`, creating it on first call."""
    global _sync_operator, _async_operator
    if _async_operator is not None:
        return _async_operator
    with _operator_lock:
        if _async_operator is None:
            _sync_operator, _async_operator = _make_operators()
    return _async_operator


def reset_operators() -> None:
    """Drop the cached operators. Intended for tests that rebind the config."""
    global _sync_operator, _async_operator
    with _operator_lock:
        _sync_operator = None
        _async_operator = None


def describe_operator() -> str:
    """Short descriptor for log / diagnostics output."""
    config = get_storage_config()
    if config.backend == "fs":
        return f"fs(root={config.fs.root})"
    if config.backend == "s3" and config.s3 is not None:
        return f"s3(endpoint={config.s3.endpoint}, bucket={config.s3.bucket})"
    return f"unknown({config.backend})"
