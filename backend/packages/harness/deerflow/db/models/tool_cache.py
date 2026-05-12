"""SQLModel row for the ``tool_cache`` table.

TTL-oriented key/value cache. ``expires_at`` is a timestamptz; reads
filter with ``expires_at > NOW()`` so expired rows are never returned,
and the periodic vacuum task deletes them by the same predicate.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Column, Field, SQLModel


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ToolCacheEntry(SQLModel, table=True):
    __tablename__ = "tool_cache"

    cache_key: str = Field(primary_key=True, nullable=False)
    tool_name: str = Field(nullable=False, index=True)
    value_json: dict[str, Any] | list[Any] = Field(
        sa_column=Column(JSONB, nullable=False),
    )
    created_at: datetime = Field(
        default_factory=_utc_now,
        nullable=False,
        sa_column_kwargs={"server_default": "NOW()"},
    )
    expires_at: datetime = Field(nullable=False)

    __table_args__ = (
        Index("idx_tool_cache_expires_at", "expires_at"),
    )
