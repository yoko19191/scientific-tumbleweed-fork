"""SQLModel row for the ``user_memory`` table.

One JSONB document per user (or the ``__global__`` sentinel). The
``version`` column supports optimistic locking: every successful write
returns ``version + 1``; concurrent writers that race on the same row
either land the update cleanly or are asked to retry.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Column, DateTime, Index, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UserMemory(SQLModel, table=True):
    __tablename__ = "user_memory"

    user_id: str = Field(primary_key=True, nullable=False)
    data: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    )
    version: int = Field(default=0, nullable=False)
    updated_at: datetime = Field(
        default_factory=_utc_now,
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=text("NOW()"),
        ),
    )

    __table_args__ = (
        Index(
            "idx_user_memory_data_gin",
            "data",
            postgresql_using="gin",
        ),
    )
