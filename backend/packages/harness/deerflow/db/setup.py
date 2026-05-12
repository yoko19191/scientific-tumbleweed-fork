"""Idempotent schema bootstrap for application-owned Postgres tables.

The **real** source of truth for the schema is ``docker/postgres/init.sql``
(emitted from the SQLModel metadata — see ``scripts/emit_init_sql.py``).
``init.sql`` runs exactly once, when the ParadeDB volume is empty.

This module is the **safety net** that runs on every gateway boot:

- In development, devs flip between branches without recreating the DB
  volume — new tables added on a branch need to materialize without
  ``docker volume rm``.
- In deployments where someone forgot to wire ``init.sql`` into the
  provisioning flow, ``ensure_schema`` still produces a working schema.

Because both paths run ``CREATE IF NOT EXISTS`` DDL, they compose safely;
a pod that finds the tables already in place is a no-op.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from deerflow.db.models import metadata as sqlmodel_metadata

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)


# Stable 64-bit int. Concurrent pods racing on schema creation both take
# this advisory lock; whoever loses waits for the winner's transaction to
# commit and then sees the schema already in place.
_SETUP_ADVISORY_LOCK_KEY = 7260524_11_01  # date-derived: 2026-05-11


# Extensions are not part of SQLModel metadata; keep them as literal DDL
# strings so they flow into both the runtime bootstrap and
# ``docker/postgres/init.sql``.
EXTENSIONS_DDL: tuple[str, ...] = (
    "CREATE EXTENSION IF NOT EXISTS vector",
    "CREATE EXTENSION IF NOT EXISTS pg_search",
    "CREATE EXTENSION IF NOT EXISTS pg_stat_statements",
)


async def ensure_schema(engine: AsyncEngine | None = None) -> None:
    """Create the application schema if it is not already in place.

    Accepts the shared :class:`AsyncEngine` from
    :mod:`deerflow.db.engine`; falls back to the module-level engine when
    nothing is passed.
    """
    if engine is None:
        from deerflow.db.engine import get_engine

        engine = get_engine()

    async with engine.begin() as conn:
        # Advisory lock — transaction-scoped so the lock is released when
        # the surrounding BEGIN commits or rolls back.
        await conn.exec_driver_sql(
            "SELECT pg_advisory_xact_lock(:key)".replace(":key", str(_SETUP_ADVISORY_LOCK_KEY))
        )
        logger.info("Running application schema setup")

        for ddl in EXTENSIONS_DDL:
            await conn.exec_driver_sql(ddl)

        # SQLModel.metadata.create_all is async-safe when driven through
        # run_sync — it inspects pg_catalog and only emits CREATE TABLE /
        # CREATE INDEX for objects that do not yet exist.
        await conn.run_sync(sqlmodel_metadata.create_all)

        logger.info("Application schema setup complete")
