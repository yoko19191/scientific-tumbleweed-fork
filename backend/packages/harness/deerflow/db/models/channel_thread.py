"""SQLModel row for the ``channel_threads`` table.

Maps ``<channel>:<chat_id>[:<topic_id>]`` to the Scientific Tumbleweed
thread that handles the conversation.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Index
from sqlmodel import Field, SQLModel


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ChannelThread(SQLModel, table=True):
    __tablename__ = "channel_threads"

    key: str = Field(primary_key=True, nullable=False)
    thread_id: str = Field(nullable=False)
    user_id: str = Field(default="", nullable=False)
    created_at: datetime = Field(
        default_factory=_utc_now,
        nullable=False,
        sa_column_kwargs={"server_default": "NOW()"},
    )
    updated_at: datetime = Field(
        default_factory=_utc_now,
        nullable=False,
        sa_column_kwargs={"server_default": "NOW()"},
    )

    __table_args__ = (
        # Supports the "remove all mappings for a chat" path which
        # scans by key prefix.
        Index(
            "idx_channel_threads_key_prefix",
            "key",
            postgresql_ops={"key": "text_pattern_ops"},
        ),
    )
