"""Singleton asyncpg connection pool for application-owned Postgres tables.

Retained as a thin adapter for callers that still want a raw asyncpg pool
(e.g. LangGraph utilities that expect a ``Pool`` object). New code should
prefer :mod:`deerflow.db.engine` (SQLAlchemy async engine + AsyncSession).

``init_pool`` is idempotent — calling it twice with the same DSN is a no-op.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from deerflow.db.dsn import resolve_dsn, to_asyncpg_dsn

if TYPE_CHECKING:
    import asyncpg

logger = logging.getLogger(__name__)

_pool: asyncpg.Pool | None = None
_pool_dsn: str | None = None


async def init_pool(
    dsn: str | None = None,
    *,
    min_size: int = 2,
    max_size: int = 20,
    command_timeout: float = 30.0,
) -> asyncpg.Pool:
    """Initialise the module-level connection pool.

    Safe to call multiple times; the first call wins. Subsequent calls with
    the same DSN return the existing pool. A DSN mismatch raises.
    """
    import asyncpg

    global _pool, _pool_dsn

    resolved = to_asyncpg_dsn(resolve_dsn(dsn))

    if _pool is not None:
        if _pool_dsn != resolved:
            raise RuntimeError(
                f"DB pool already initialised with a different DSN "
                f"(existing={_pool_dsn!r}, requested={resolved!r})"
            )
        return _pool

    logger.info("Initialising asyncpg pool (min=%d, max=%d)", min_size, max_size)
    _pool = await asyncpg.create_pool(
        dsn=resolved,
        min_size=min_size,
        max_size=max_size,
        command_timeout=command_timeout,
    )
    _pool_dsn = resolved
    logger.info("asyncpg pool ready")
    return _pool


def get_pool() -> asyncpg.Pool:
    """Return the initialised pool, or raise if not initialised."""
    if _pool is None:
        raise RuntimeError(
            "DB pool is not initialised. Call deerflow.db.init_pool() during "
            "application startup (e.g. FastAPI lifespan)."
        )
    return _pool


def is_initialized() -> bool:
    """Return True if the pool has been initialised."""
    return _pool is not None


async def close_pool() -> None:
    """Close the pool and release resources. Idempotent."""
    global _pool, _pool_dsn
    if _pool is None:
        return
    logger.info("Closing asyncpg pool")
    await _pool.close()
    _pool = None
    _pool_dsn = None
