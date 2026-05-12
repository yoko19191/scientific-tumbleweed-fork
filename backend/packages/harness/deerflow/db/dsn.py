"""Shared DSN resolver used by every Postgres client in the project.

Single source of truth for the connection string. Centralising this here
means ``deerflow.db.pool`` (asyncpg), ``deerflow.db.engine`` (SQLAlchemy +
SQLModel), and the few remaining psycopg pools all resolve the DSN the
same way and never drift.

Resolution order:

1. explicit argument to :func:`resolve_dsn`
2. ``POSTGRES_DSN`` environment variable
3. ``checkpointer.connection_string`` from ``config.yaml`` (with ``$VAR``
   expansion mirroring :mod:`deerflow.config.app_config`)
"""

from __future__ import annotations

import os


def _expand_env(value: str) -> str:
    """Expand a leading ``$VAR`` reference the same way app_config.py does."""
    if value.startswith("$"):
        expanded = os.getenv(value[1:])
        if not expanded:
            raise RuntimeError(f"Environment variable {value[1:]} is not set")
        return expanded
    return value


def resolve_dsn(explicit: str | None = None) -> str:
    """Return the Postgres DSN to use, raising if none is configured."""
    if explicit:
        return _expand_env(explicit)

    env_dsn = os.getenv("POSTGRES_DSN")
    if env_dsn:
        return env_dsn

    try:
        from deerflow.config.checkpointer_config import get_checkpointer_config

        cp_config = get_checkpointer_config()
        if cp_config and cp_config.type == "postgres" and cp_config.connection_string:
            return _expand_env(cp_config.connection_string)
    except Exception:
        # Config not loaded yet or import failure — the caller must supply DSN.
        pass

    raise RuntimeError(
        "Cannot resolve Postgres DSN. Set POSTGRES_DSN environment variable "
        "or configure checkpointer.connection_string in config.yaml."
    )


def to_asyncpg_dsn(dsn: str) -> str:
    """Normalise an SQLAlchemy-style URL to something ``asyncpg`` accepts."""
    # SQLAlchemy accepts ``postgresql+asyncpg://``; asyncpg itself rejects the
    # ``+asyncpg`` suffix. Strip any driver marker so the same DSN works in
    # both places.
    for prefix in ("postgresql+asyncpg://", "postgres+asyncpg://"):
        if dsn.startswith(prefix):
            return "postgresql://" + dsn[len(prefix):]
    return dsn


def to_sqlalchemy_async_dsn(dsn: str) -> str:
    """Return a DSN that SQLAlchemy's async engine can consume."""
    if dsn.startswith("postgresql+asyncpg://"):
        return dsn
    if dsn.startswith("postgres://"):
        return "postgresql+asyncpg://" + dsn[len("postgres://"):]
    if dsn.startswith("postgresql://"):
        return "postgresql+asyncpg://" + dsn[len("postgresql://"):]
    # Anything else (e.g. an already-prefixed driver) is passed through.
    return dsn
