"""baseline — application tables (users, user_memory, tool_cache, channel_threads).

Revision ID: e35828dc111e
Revises:
Create Date: 2026-05-13 01:56:49

This migration is intentionally empty. The four application-owned tables
are created either by:

  * ``docker/postgres/init.sql``, which runs on first container boot
    when the PG volume is empty, or
  * ``deerflow.db.setup.ensure_schema()`` (SQLModel ``metadata.create_all``),
    which the gateway runs on every startup as an idempotent safety net.

On a fresh database, stamp Alembic as up-to-date so subsequent
revisions can run incrementally::

    uv run alembic -c backend/alembic.ini stamp head

All schema changes after this baseline should go through Alembic
``revision --autogenerate`` + ``upgrade head``.
"""

from __future__ import annotations

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "e35828dc111e"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """No-op — schema established by init.sql / ensure_schema()."""


def downgrade() -> None:
    """No-op — downgrading past the baseline would drop live data."""
