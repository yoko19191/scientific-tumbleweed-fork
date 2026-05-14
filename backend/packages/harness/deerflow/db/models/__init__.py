"""SQLModel definitions for application-owned Postgres tables.

Importing ``deerflow.db.models`` is enough to have all table metadata
registered on the shared SQLModel ``MetaData`` — the submodules import
themselves into this package on first access.

When adding a new table:

1. Create a new module under ``deerflow/db/models/`` and ``table=True``
2. Import it here so ``SQLModel.metadata`` picks it up
3. Regenerate ``docker/postgres/init.sql`` with ``make emit-init-sql``
"""

from __future__ import annotations

from sqlmodel import SQLModel

from deerflow.db.models.channel_thread import ChannelThread
from deerflow.db.models.tool_cache import ToolCacheEntry
from deerflow.db.models.user import User
from deerflow.db.models.user_memory import UserMemory

__all__ = [
    "ChannelThread",
    "SQLModel",
    "ToolCacheEntry",
    "User",
    "UserMemory",
    "metadata",
]

# Re-exported so callers don't have to know which submodule owns the metadata.
metadata = SQLModel.metadata
