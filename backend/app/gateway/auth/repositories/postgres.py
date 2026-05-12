"""PostgreSQL implementation of :class:`UserRepository` via SQLModel.

Uses the shared SQLAlchemy async engine from :mod:`deerflow.db`. Error
messages are kept bit-for-bit identical to the sqlite repository so
auth callers behave the same regardless of backend.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlmodel import func, select

from app.gateway.auth.models import User as AppUser
from app.gateway.auth.repositories.base import UserRepository
from deerflow.db.models import User as UserRow

if TYPE_CHECKING:
    from sqlalchemy.orm import sessionmaker
    from sqlmodel.ext.asyncio.session import AsyncSession


class PostgresUserRepository(UserRepository):
    """SQLModel-backed user repository."""

    def __init__(self, session_factory: sessionmaker[AsyncSession] | None = None) -> None:
        """Accept a session factory for tests; defaults to the module-level one."""
        self._factory = session_factory

    # ------------------------------------------------------------------
    # Session helper
    # ------------------------------------------------------------------

    def _get_factory(self) -> sessionmaker[AsyncSession]:
        if self._factory is not None:
            return self._factory
        from deerflow.db import get_session_factory

        return get_session_factory()

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    async def create_user(self, user: AppUser) -> AppUser:
        row = _app_to_row(user)
        factory = self._get_factory()
        async with factory() as session:
            session.add(row)
            try:
                await session.commit()
            except IntegrityError as exc:
                await session.rollback()
                # asyncpg surfaces the constraint name inside the DB exception;
                # SQLAlchemy wraps it in IntegrityError.orig. Look for the
                # constraint name in the full text of the error.
                detail = str(exc).lower()
                if "users_email_key" in detail or "email" in detail:
                    raise ValueError(f"Email already registered: {user.email}") from exc
                if "users_username_key" in detail or "username" in detail:
                    raise ValueError(f"Username already taken: {user.username}") from exc
                raise
        return user

    async def update_user(self, user: AppUser) -> AppUser:
        factory = self._get_factory()
        async with factory() as session:
            existing = await session.get(UserRow, str(user.id))
            if existing is None:
                # Mirror sqlite repository behaviour: a missing row is an
                # explicit no-op followed by returning the supplied object.
                return user
            existing.email = user.email
            existing.username = user.username
            existing.display_name = user.display_name
            existing.password_hash = user.password_hash
            existing.system_role = user.system_role
            existing.oauth_provider = user.oauth_provider
            existing.oauth_id = user.oauth_id
            existing.needs_setup = bool(user.needs_setup)
            existing.token_version = int(user.token_version)
            await session.commit()
        return user

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    async def get_user_by_id(self, user_id: str) -> AppUser | None:
        factory = self._get_factory()
        async with factory() as session:
            row = await session.get(UserRow, user_id)
            return _row_to_app(row) if row else None

    async def get_user_by_email(self, email: str) -> AppUser | None:
        return await self._first_where(UserRow.email == email)

    async def get_user_by_username(self, username: str) -> AppUser | None:
        return await self._first_where(UserRow.username == username)

    async def get_user_by_oauth(self, provider: str, oauth_id: str) -> AppUser | None:
        factory = self._get_factory()
        async with factory() as session:
            stmt = select(UserRow).where(
                UserRow.oauth_provider == provider,
                UserRow.oauth_id == oauth_id,
            )
            result = await session.exec(stmt)
            row = result.first()
            return _row_to_app(row) if row else None

    async def count_users(self) -> int:
        factory = self._get_factory()
        async with factory() as session:
            result = await session.exec(select(func.count()).select_from(UserRow))
            return int(result.one())

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _first_where(self, predicate) -> AppUser | None:
        factory = self._get_factory()
        async with factory() as session:
            result = await session.exec(select(UserRow).where(predicate))
            row = result.first()
            return _row_to_app(row) if row else None


# ---------------------------------------------------------------------------
# Row <-> API model mapping
# ---------------------------------------------------------------------------


def _app_to_row(user: AppUser) -> UserRow:
    created_at = user.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    return UserRow(
        id=str(user.id),
        email=user.email,
        username=user.username,
        display_name=user.display_name,
        password_hash=user.password_hash,
        system_role=user.system_role,
        created_at=created_at,
        oauth_provider=user.oauth_provider,
        oauth_id=user.oauth_id,
        needs_setup=bool(user.needs_setup),
        token_version=int(user.token_version),
    )


def _row_to_app(row: UserRow) -> AppUser:
    created_at = row.created_at
    if isinstance(created_at, datetime) and created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    return AppUser(
        id=UUID(row.id),
        email=row.email,
        username=row.username or "",
        display_name=row.display_name or "",
        password_hash=row.password_hash,
        system_role=row.system_role,
        created_at=created_at,
        oauth_provider=row.oauth_provider,
        oauth_id=row.oauth_id,
        needs_setup=bool(row.needs_setup),
        token_version=int(row.token_version),
    )
