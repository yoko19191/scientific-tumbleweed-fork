"""Alembic environment.

Uses the same DSN resolver as :mod:`deerflow.db.engine` so migrations
target whatever Postgres the running application is already pointed at.
SQLModel metadata is the source of truth for what should exist, so the
``--autogenerate`` flag can diff it against the live schema.

Important scope decision: alembic only manages the four
**application-owned** tables (``users``, ``user_memory``, ``tool_cache``,
``channel_threads``) plus any future SQLModel additions. Tables created
by other tools (LangGraph's ``checkpoints*`` / ``store*``, PostGIS, etc.)
are filtered out via ``include_object`` so autogenerate never proposes
to drop them.
"""

from __future__ import annotations

import os

from alembic import context
from sqlalchemy import engine_from_config, pool

from deerflow.db.dsn import resolve_dsn, to_sqlalchemy_async_dsn
from deerflow.db.models import metadata as sqlmodel_metadata

config = context.config

# Inject the live DSN. Alembic uses a regular SQLAlchemy engine, so force
# the sync psycopg3 driver.
_async_dsn = to_sqlalchemy_async_dsn(resolve_dsn(os.environ.get("POSTGRES_DSN")))
_sync_dsn = _async_dsn.replace("+asyncpg", "+psycopg")
config.set_main_option("sqlalchemy.url", _sync_dsn)

target_metadata = sqlmodel_metadata

# Tables we are responsible for — anything outside this set is filtered
# out of autogenerate diffs.
_MANAGED_TABLES = frozenset(sqlmodel_metadata.tables.keys())


def _include_object(obj, name, type_, reflected, compare_to):
    """Skip objects that don't belong to our SQLModel metadata.

    LangGraph creates its own checkpointer/store schema on first boot;
    we should never try to migrate or drop those tables.
    """
    if type_ == "table":
        return name in _MANAGED_TABLES
    if type_ == "index":
        # Indexes attached to managed tables are picked up automatically
        # via their `.table` attribute.
        table = getattr(obj, "table", None)
        if table is not None and table.name not in _MANAGED_TABLES:
            return False
    return True


def run_migrations_offline() -> None:
    """Emit SQL scripts without connecting to the database."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=False,
        include_object=_include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations with a live connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=False,
            include_object=_include_object,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
