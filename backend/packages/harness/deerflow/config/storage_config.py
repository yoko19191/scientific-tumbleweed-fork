"""Configuration for the OpenDAL-backed object storage layer.

The `storage` block in ``config.yaml`` drives this:

.. code-block:: yaml

    storage:
      backend: fs
      fs:
        root: .deer-flow/storage
      # s3:
      #   endpoint: http://minio:9000
      #   bucket: scientifictumbleweed
      #   access_key_id: $MINIO_ACCESS_KEY
      #   secret_access_key: $MINIO_SECRET_KEY
      #   region: us-east-1

Each backend carries exactly the knobs the underlying OpenDAL scheme
needs.  Adding a new backend later (Azure, GCS, …) means a new pydantic
class here and a new branch in :func:`make_operator`.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class FilesystemStorageConfig(BaseModel):
    """Store objects on the local filesystem under ``root``."""

    root: str = Field(
        default=".deer-flow/storage",
        description=(
            "Directory that backs the ``fs`` OpenDAL operator. Relative "
            "paths are resolved against the application working directory. "
            "Mounted into the gateway container in the dev compose file."
        ),
    )


class S3StorageConfig(BaseModel):
    """S3-compatible store (MinIO, AWS S3, Cloud OSS, ...)."""

    endpoint: str = Field(..., description="S3 endpoint URL, e.g. http://minio:9000")
    bucket: str = Field(..., description="Bucket name.")
    region: str = Field(default="us-east-1", description="Region hint for signing.")
    access_key_id: str = Field(default="", description="Access key (or empty for IAM).")
    secret_access_key: str = Field(default="", description="Secret key (or empty for IAM).")
    root: str = Field(
        default="/",
        description="Optional prefix inside the bucket; leading slash is allowed.",
    )


BackendName = Literal["fs", "s3"]


class StorageConfig(BaseModel):
    """Top-level storage configuration."""

    backend: BackendName = Field(
        default="fs",
        description="Which OpenDAL backend to build. Supported: fs, s3.",
    )
    fs: FilesystemStorageConfig = Field(default_factory=FilesystemStorageConfig)
    s3: S3StorageConfig | None = Field(
        default=None,
        description="Required when ``backend='s3'``. Omit for ``backend='fs'``.",
    )


_storage_config: StorageConfig | None = None


def get_storage_config() -> StorageConfig:
    """Return the current storage configuration, defaulting to local ``fs``."""
    global _storage_config
    if _storage_config is None:
        _storage_config = StorageConfig()
    return _storage_config


def set_storage_config(config: StorageConfig) -> None:
    """Replace the global config. Used at startup and from tests."""
    global _storage_config
    _storage_config = config


def load_storage_config_from_dict(config_dict: dict) -> None:
    """Load storage configuration from a plain dict (e.g. config.yaml section)."""
    global _storage_config
    _storage_config = StorageConfig(**config_dict)
