"""SQLModel row for the ``users`` table.

Mirrors the schema that Round 1 created through raw DDL (see
``deerflow.db.setup._USERS_DDL``). Columns, defaults, and the three
unique constraints (email, username, and the partial OAuth identity
index) are preserved so existing data and existing repositories stay
compatible.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Index, text
from sqlmodel import Field, SQLModel


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: str = Field(primary_key=True, sa_column_kwargs={"nullable": False})
    email: str = Field(nullable=False, index=False, unique=True)
    username: str = Field(default="", nullable=False, unique=True)
    display_name: str = Field(default="", nullable=False)
    password_hash: str | None = Field(default=None, nullable=True)
    system_role: str = Field(default="user", nullable=False)
    created_at: datetime = Field(
        default_factory=_utc_now,
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=text("NOW()"),
        ),
    )
    oauth_provider: str | None = Field(default=None, nullable=True)
    oauth_id: str | None = Field(default=None, nullable=True)
    needs_setup: bool = Field(default=False, nullable=False)
    token_version: int = Field(default=0, nullable=False)

    __table_args__ = (
        Index(
            "idx_users_oauth_identity",
            "oauth_provider",
            "oauth_id",
            unique=True,
            postgresql_where="oauth_provider IS NOT NULL AND oauth_id IS NOT NULL",
        ),
    )
