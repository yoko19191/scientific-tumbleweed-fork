"""SQLAlchemy async engine + session factory.

This is the **preferred** way for new code to talk to Postgres. The
legacy asyncpg pool in :mod:`deerflow.db.pool` is kept only for callers
that need a raw ``asyncpg.Pool`` object (for example the one-off
``ensure_schema`` advisory-lock transaction).

Typical usage in a FastAPI lifespan::

    from deerflow.db import init_engine, close_engine
    engine = await init_engine()
    await ensure_schema(engine)
    ...
    await close_engine()

Inside request handlers / repositories, accept an ``AsyncSession`` via
dependency injection, or use the module-level ``session_scope`` helper
for one-off work::

    from deerflow.db.engine import session_scope
    async with session_scope() as session:
        result = await session.exec(select(User).where(User.email == email))
        user = result.first()
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from deerflow.db.dsn import resolve_dsn, to_sqlalchemy_async_dsn

logger = logging.getLogger(__name__)

_engine: AsyncEngine | None = None
_session_factory: sessionmaker[AsyncSession] | None = None
_engine_dsn: str | None = None


async def init_engine(
    dsn: str | None = None,
    *,
    pool_size: int = 10,
    max_overflow: int = 20,
    pool_pre_ping: bool = True,
    echo: bool = False,
) -> AsyncEngine:
    """Create (or return) the module-level async engine + session factory.

    Safe to call multiple times; later calls must use the same DSN or the
    function raises.
    """
    global _engine, _session_factory, _engine_dsn

    resolved = to_sqlalchemy_async_dsn(resolve_dsn(dsn))

    if _engine is not None:
        if _engine_dsn != resolved:
            raise RuntimeError(
                f"DB engine already initialised with a different DSN "
                f"(existing={_engine_dsn!r}, requested={resolved!r})"
            )
        return _engine

    logger.info(
        "Initialising SQLAlchemy async engine (pool_size=%d, max_overflow=%d)",
        pool_size,
        max_overflow,
    )
    _engine = create_async_engine(
        resolved,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_pre_ping=pool_pre_ping,
        echo=echo,
    )
    # We use SQLModel's AsyncSession subclass so `session.exec(select(Model))`
    # returns typed model instances instead of a generic SQLAlchemy Row tuple.
    _session_factory = sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    _engine_dsn = resolved
    logger.info("SQLAlchemy async engine ready")
    return _engine


def get_engine() -> AsyncEngine:
    if _engine is None:
        raise RuntimeError(
            "DB engine is not initialised. Call deerflow.db.init_engine() "
            "during application startup (e.g. FastAPI lifespan)."
        )
    return _engine


def get_session_factory() -> sessionmaker[AsyncSession]:
    if _session_factory is None:
        raise RuntimeError(
            "Session factory is not initialised. Call deerflow.db.init_engine() "
            "first."
        )
    return _session_factory


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """Short-lived session for one-off queries outside a FastAPI request."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def close_engine() -> None:
    """Dispose the engine. Idempotent."""
    global _engine, _session_factory, _engine_dsn
    if _engine is None:
        return
    logger.info("Disposing SQLAlchemy async engine")
    await _engine.dispose()
    _engine = None
    _session_factory = None
    _engine_dsn = None
