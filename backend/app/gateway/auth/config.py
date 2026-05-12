"""Authentication configuration for Scientific Tumbleweed."""

import logging
import os
import secrets
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()

logger = logging.getLogger(__name__)


class AuthConfig(BaseModel):
    """JWT and auth-related configuration. Parsed once at startup."""

    jwt_secret: str = Field(
        ...,
        description="Secret key for JWT signing. MUST be set via AUTH_JWT_SECRET.",
    )
    token_expiry_days: int = Field(default=7, ge=1, le=30)
    repository_backend: Literal["postgres", "sqlite"] = Field(
        default="postgres",
        description=(
            "Storage backend for users. Default 'postgres' uses the shared "
            "asyncpg pool from deerflow.db (production). 'sqlite' keeps the "
            "legacy .deer-flow/users.db path (tests / single-file mode). "
            "Override via AUTH_REPOSITORY_BACKEND env var."
        ),
    )
    users_db_path: str | None = Field(
        default=None,
        description=(
            "Legacy SQLite database path. Used only when repository_backend='sqlite'. "
            "Defaults to .deer-flow/users.db when sqlite backend is selected."
        ),
    )
    oauth_github_client_id: str | None = Field(default=None)
    oauth_github_client_secret: str | None = Field(default=None)


_auth_config: AuthConfig | None = None


def get_auth_config() -> AuthConfig:
    """Get the global AuthConfig instance. Parses from env on first call."""
    global _auth_config
    if _auth_config is None:
        jwt_secret = os.environ.get("AUTH_JWT_SECRET")
        if not jwt_secret:
            jwt_secret = secrets.token_urlsafe(32)
            os.environ["AUTH_JWT_SECRET"] = jwt_secret
            logger.warning(
                "⚠ AUTH_JWT_SECRET is not set — using an auto-generated ephemeral secret. "
                "Sessions will be invalidated on restart. "
                "For production, add AUTH_JWT_SECRET to your .env file: "
                'python -c "import secrets; print(secrets.token_urlsafe(32))"'
            )
        backend = os.environ.get("AUTH_REPOSITORY_BACKEND", "postgres").strip().lower()
        if backend not in ("postgres", "sqlite"):
            logger.warning(
                "Invalid AUTH_REPOSITORY_BACKEND=%r; falling back to 'postgres'", backend
            )
            backend = "postgres"
        _auth_config = AuthConfig(
            jwt_secret=jwt_secret,
            repository_backend=backend,  # type: ignore[arg-type]
        )
    return _auth_config


def set_auth_config(config: AuthConfig) -> None:
    """Set the global AuthConfig instance (for testing)."""
    global _auth_config
    _auth_config = config
