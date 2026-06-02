from __future__ import annotations

from app.gateway.routers import upload_config


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
