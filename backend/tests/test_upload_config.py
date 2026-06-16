from __future__ import annotations

from unittest.mock import patch

from app.gateway.routers import upload_config
from deerflow.uploads.limits import UploadLimits


def test_parse_nginx_size_units() -> None:
    assert upload_config._parse_nginx_size("100M") == 100 * 1024 * 1024
    assert upload_config._parse_nginx_size("2g") == 2 * 1024 * 1024 * 1024
    assert upload_config._parse_nginx_size("512k") == 512 * 1024
    assert upload_config._parse_nginx_size("4096") == 4096


def test_parse_nginx_size_zero_means_unlimited() -> None:
    assert upload_config._parse_nginx_size("0") is None


def test_finds_upload_location_client_max_body_size() -> None:
    content = """
    http {
        client_max_body_size 10M;

        server {
            location ~ ^/api/threads/[^/]+/uploads {
                client_max_body_size 125M;
            }
        }
    }
    """

    assert upload_config._find_client_max_body_size(content) == "125M"


def test_falls_back_to_global_client_max_body_size() -> None:
    content = """
    http {
        client_max_body_size 10M;
    }
    """

    assert upload_config._find_client_max_body_size(content) == "10M"


def test_read_upload_limit_includes_app_limits_and_nginx_total_cap(tmp_path) -> None:
    nginx_config = tmp_path / "nginx.conf"
    nginx_config.write_text("client_max_body_size 20M;\n", encoding="utf-8")

    with (
        patch.object(upload_config, "_nginx_config_candidates", return_value=(nginx_config,)),
        patch.object(
            upload_config,
            "get_upload_limits",
            return_value=UploadLimits(max_files=3, max_file_size=10 * 1024 * 1024, max_total_size=30 * 1024 * 1024),
        ),
    ):
        result = upload_config._read_upload_limit()

    assert result.max_files == 3
    assert result.max_file_size == 10 * 1024 * 1024
    assert result.max_body_bytes == 20 * 1024 * 1024
    assert result.max_total_size == 20 * 1024 * 1024
