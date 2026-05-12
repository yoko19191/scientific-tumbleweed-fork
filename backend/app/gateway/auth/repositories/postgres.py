"""PostgreSQL implementation of UserRepository.

Backed by the shared asyncpg pool from :mod:`deerflow.db`.
Mirrors :class:`SQLiteUserRepository` semantics exactly — same error
messages (``"Email already registered: ..."``, ``"Username already taken: ..."``)
so callers behave identically regardless of backend.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from app.gateway.auth.models import User
from app.gateway.auth.repositories.base import UserRepository

if TYPE_CHECKING:
    import asyncpg


# Columns in SELECT order — keep in sync with _row_to_user.
_SELECT_COLUMNS = (
    "id, email, username, display_name, password_hash, system_role, "
    "created_at, oauth_provider, oauth_id, needs_setup, token_version"
)


class PostgresUserRepository(UserRepository):
    """PostgreSQL implementation of :class:`UserRepository`."""

    def __init__(self, pool: asyncpg.Pool | None = None) -> None:
        """Accept an optional pool for tests; defaults to the global pool."""
        self._pool = pool

    def _get_pool(self) -> asyncpg.Pool:
        if self._pool is not None:
            return self._pool
        from deerflow.db import get_pool

        return get_pool()

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    async def create_user(self, user: User) -> User:
        import asyncpg

        pool = self._get_pool()
        try:
            await pool.execute(
                f"""
                INSERT INTO users ({_SELECT_COLUMNS})
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                """,
                str(user.id),
                user.email,
                user.username,
                user.display_name,
                user.password_hash,
                user.system_role,
                user.created_at if user.created_at.tzinfo else user.created_at.replace(tzinfo=UTC),
                user.oauth_provider,
                user.oauth_id,
                bool(user.needs_setup),
                int(user.token_version),
            )
        except asyncpg.UniqueViolationError as exc:
            # Translate constraint names into the same messages the
            # SQLite backend emits — callers (auth service) match on them.
            constraint = getattr(exc, "constraint_name", "") or ""
            detail = str(exc)
            if "users_email_key" in constraint or "email" in detail.lower():
                raise ValueError(f"Email already registered: {user.email}") from exc
            if "users_username_key" in constraint or "username" in detail.lower():
                raise ValueError(f"Username already taken: {user.username}") from exc
            raise
        return user

    async def update_user(self, user: User) -> User:
        pool = self._get_pool()
        await pool.execute(
            """
            UPDATE users
               SET email = $1,
                   username = $2,
                   display_name = $3,
                   password_hash = $4,
                   system_role = $5,
                   oauth_provider = $6,
                   oauth_id = $7,
                   needs_setup = $8,
                   token_version = $9
             WHERE id = $10
            """,
            user.email,
            user.username,
            user.display_name,
            user.password_hash,
            user.system_role,
            user.oauth_provider,
            user.oauth_id,
            bool(user.needs_setup),
            int(user.token_version),
            str(user.id),
        )
        return user

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    async def get_user_by_id(self, user_id: str) -> User | None:
        pool = self._get_pool()
        row = await pool.fetchrow(
            f"SELECT {_SELECT_COLUMNS} FROM users WHERE id = $1", user_id
        )
        return self._row_to_user(row) if row else None

    async def get_user_by_email(self, email: str) -> User | None:
        pool = self._get_pool()
        row = await pool.fetchrow(
            f"SELECT {_SELECT_COLUMNS} FROM users WHERE email = $1", email
        )
        return self._row_to_user(row) if row else None

    async def get_user_by_username(self, username: str) -> User | None:
        pool = self._get_pool()
        row = await pool.fetchrow(
            f"SELECT {_SELECT_COLUMNS} FROM users WHERE username = $1", username
        )
        return self._row_to_user(row) if row else None

    async def get_user_by_oauth(self, provider: str, oauth_id: str) -> User | None:
        pool = self._get_pool()
        row = await pool.fetchrow(
            f"SELECT {_SELECT_COLUMNS} FROM users WHERE oauth_provider = $1 AND oauth_id = $2",
            provider,
            oauth_id,
        )
        return self._row_to_user(row) if row else None

    async def count_users(self) -> int:
        pool = self._get_pool()
        result = await pool.fetchval("SELECT COUNT(*) FROM users")
        return int(result or 0)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_user(row: asyncpg.Record) -> User:
        created_at = row["created_at"]
        if isinstance(created_at, datetime) and created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        return User(
            id=UUID(row["id"]),
            email=row["email"],
            username=row["username"] or "",
            display_name=row["display_name"] or "",
            password_hash=row["password_hash"],
            system_role=row["system_role"],
            created_at=created_at,
            oauth_provider=row["oauth_provider"],
            oauth_id=row["oauth_id"],
            needs_setup=bool(row["needs_setup"]),
            token_version=int(row["token_version"]),
        )
