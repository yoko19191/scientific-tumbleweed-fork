"""Singleton asyncpg connection pool for application-owned Postgres tables.

The DSN is resolved from (in priority order):
1. explicit ``dsn`` parameter passed to :func:`init_pool`
2. ``POSTGRES_DSN`` environment variable
3. LangGraph checkpointer config's ``connection_string`` (so we share the
   same database as checkpointer/store by default)

``init_pool`` is idempotent — calling it twice with the same DSN is a no-op.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import asyncpg

logger = logging.getLogger(__name__)

_pool: asyncpg.Pool | None = None
_pool_dsn: str | None = None


def _resolve_dsn(explicit: str | None = None) -> str:
    """Resolve the DSN from parameter → env → checkpointer config."""
    if explicit:
        return _expand_env(explicit)

    env_dsn = os.getenv("POSTGRES_DSN")
    if env_dsn:
        return env_dsn

    # Fall back to the checkpointer's DSN so we don't duplicate config.
    try:
        from deerflow.config.checkpointer_config import get_checkpointer_config

        cp_config = get_checkpointer_config()
        if cp_config and cp_config.type == "postgres" and cp_config.connection_string:
            return _expand_env(cp_config.connection_string)
    except Exception:
        # Config not loaded yet or import failure — caller must supply DSN.
        pass

    raise RuntimeError(
        "Cannot resolve Postgres DSN. Set POSTGRES_DSN environment variable "
        "or configure checkpointer.connection_string in config.yaml."
    )


def _expand_env(value: str) -> str:
    """Expand a leading ``$VAR`` reference the same way app_config.py does."""
    if value.startswith("$"):
        expanded = os.getenv(value[1:])
        if not expanded:
            raise RuntimeError(f"Environment variable {value[1:]} is not set")
        return expanded
    return value


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

    resolved = _resolve_dsn(dsn)

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
