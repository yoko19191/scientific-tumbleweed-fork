from types import SimpleNamespace

from deerflow.uploads.limits import (
    DEFAULT_UPLOAD_MAX_FILE_SIZE,
    DEFAULT_UPLOAD_MAX_FILES,
    UploadLimits,
    get_upload_limits,
)


def test_get_upload_limits_parses_string_sizes() -> None:
    config = SimpleNamespace(
        uploads={
            "max_files": "3",
            "max_file_size": "5MiB",
            "max_total_size": "20M",
        }
    )

    assert get_upload_limits(config) == UploadLimits(
        max_files=3,
        max_file_size=5 * 1024 * 1024,
        max_total_size=20 * 1024 * 1024,
    )


def test_get_upload_limits_uses_defaults_for_invalid_values() -> None:
    config = SimpleNamespace(
        uploads={
            "max_files": 0,
            "max_file_size": "not-a-size",
            "max_total_size": False,
        }
    )

    limits = get_upload_limits(config)

    assert limits.max_files == DEFAULT_UPLOAD_MAX_FILES
    assert limits.max_file_size == DEFAULT_UPLOAD_MAX_FILE_SIZE
