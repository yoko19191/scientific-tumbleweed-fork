"""SQLModel row for the ``tool_cache`` table.

TTL-oriented key/value cache. ``expires_at`` is a timestamptz; reads
filter with ``expires_at > NOW()`` so expired rows are never returned,
and the periodic vacuum task deletes them by the same predicate.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Column, DateTime, Index, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


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
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=text("NOW()"),
        ),
    )
    expires_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
        ),
    )

    __table_args__ = (
        Index("idx_tool_cache_expires_at", "expires_at"),
    )
