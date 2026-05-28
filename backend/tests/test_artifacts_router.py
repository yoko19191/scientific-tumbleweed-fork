import asyncio
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request
from starlette.responses import FileResponse

import app.gateway.routers.artifacts as artifacts_router

USER_A = "user-aaaa-1111"

ACTIVE_ARTIFACT_CASES = [
    ("poc.html", "<html><body><script>alert('xss')</script></body></html>"),
    ("page.xhtml", '<?xml version="1.0"?><html xmlns="http://www.w3.org/1999/xhtml"><body>hello</body></html>'),
    ("image.svg", '<svg xmlns="http://www.w3.org/2000/svg"><script>alert("xss")</script></svg>'),
]


def _make_request(query_string: bytes = b"") -> Request:
    return Request({"type": "http", "method": "GET", "path": "/", "headers": [], "query_string": query_string})


def _patch_resolved_thread_path(monkeypatch, resolved_path: Path, user_id: str = USER_A):
    resource = SimpleNamespace(user_id=user_id, resolve_virtual_path=lambda _path: resolved_path)
    monkeypatch.setattr(artifacts_router, "get_authenticated_thread_resource", AsyncMock(return_value=resource))


def test_get_artifact_reads_utf8_text_file_on_windows_locale(tmp_path, monkeypatch) -> None:
    artifact_path = tmp_path / "note.txt"
    text = "Curly quotes: \u201cutf8\u201d"
    artifact_path.write_text(text, encoding="utf-8")

    original_read_text = Path.read_text

    def read_text_with_gbk_default(self, *args, **kwargs):
        kwargs.setdefault("encoding", "gbk")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read_text_with_gbk_default)
    _patch_resolved_thread_path(monkeypatch, artifact_path)

    request = _make_request()
    response = asyncio.run(artifacts_router.get_artifact("thread-1", "mnt/user-data/outputs/note.txt", request))

    assert bytes(response.body).decode("utf-8") == text
    assert response.media_type == "text/plain"


def test_get_artifact_resolves_path_through_authenticated_resource(tmp_path, monkeypatch) -> None:
    artifact_path = tmp_path / "note.txt"
    artifact_path.write_text("hello", encoding="utf-8")
    resource = SimpleNamespace(user_id=USER_A, resolve_virtual_path=Mock(return_value=artifact_path))
    get_resource = AsyncMock(return_value=resource)
    monkeypatch.setattr(artifacts_router, "get_authenticated_thread_resource", get_resource)

    response = asyncio.run(artifacts_router.get_artifact("thread-1", "mnt/user-data/outputs/note.txt", _make_request()))

    assert response.body == b"hello"
    get_resource.assert_awaited_once()
    resource.resolve_virtual_path.assert_called_once_with("mnt/user-data/outputs/note.txt")


@pytest.mark.parametrize(("filename", "content"), ACTIVE_ARTIFACT_CASES)
def test_get_artifact_forces_download_for_active_content(tmp_path, monkeypatch, filename: str, content: str) -> None:
    artifact_path = tmp_path / filename
    artifact_path.write_text(content, encoding="utf-8")

    _patch_resolved_thread_path(monkeypatch, artifact_path)

    response = asyncio.run(artifacts_router.get_artifact("thread-1", f"mnt/user-data/outputs/{filename}", _make_request()))

    assert isinstance(response, FileResponse)
    assert response.headers.get("content-disposition", "").startswith("attachment;")


@pytest.mark.parametrize(("filename", "content"), ACTIVE_ARTIFACT_CASES)
def test_get_artifact_forces_download_for_active_content_in_skill_archive(tmp_path, monkeypatch, filename: str, content: str) -> None:
    skill_path = tmp_path / "sample.skill"
    with zipfile.ZipFile(skill_path, "w") as zip_ref:
        zip_ref.writestr(filename, content)

    _patch_resolved_thread_path(monkeypatch, skill_path)

    response = asyncio.run(artifacts_router.get_artifact("thread-1", f"mnt/user-data/outputs/sample.skill/{filename}", _make_request()))

    assert response.headers.get("content-disposition", "").startswith("attachment;")
    assert bytes(response.body) == content.encode("utf-8")


def test_get_artifact_download_false_does_not_force_attachment(tmp_path, monkeypatch) -> None:
    artifact_path = tmp_path / "note.txt"
    artifact_path.write_text("hello", encoding="utf-8")

    _patch_resolved_thread_path(monkeypatch, artifact_path)

    app = FastAPI()
    app.include_router(artifacts_router.router)

    with TestClient(app) as client:
        response = client.get("/api/threads/thread-1/artifacts/mnt/user-data/outputs/note.txt?download=false")

    assert response.status_code == 200
    assert response.text == "hello"
    assert "content-disposition" not in response.headers


def test_get_artifact_download_true_forces_attachment_for_skill_archive(tmp_path, monkeypatch) -> None:
    skill_path = tmp_path / "sample.skill"
    with zipfile.ZipFile(skill_path, "w") as zip_ref:
        zip_ref.writestr("notes.txt", "hello")

    _patch_resolved_thread_path(monkeypatch, skill_path)

    app = FastAPI()
    app.include_router(artifacts_router.router)

    with TestClient(app) as client:
        response = client.get("/api/threads/thread-1/artifacts/mnt/user-data/outputs/sample.skill/notes.txt?download=true")

    assert response.status_code == 200
    assert response.text == "hello"
    assert response.headers.get("content-disposition", "").startswith("attachment;")


# ---------------------------------------------------------------------------
# US-012: Unauthenticated access returns 401
# ---------------------------------------------------------------------------


def test_get_artifact_returns_401_when_unauthenticated() -> None:
    """Artifact endpoint must return 401 when no valid session cookie."""
    app = FastAPI()
    app.include_router(artifacts_router.router)

    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.get("/api/threads/thread-1/artifacts/mnt/user-data/outputs/file.txt")
    assert resp.status_code == 401


def test_get_artifact_skill_archive_returns_401_when_unauthenticated() -> None:
    """Artifact skill archive endpoint must return 401 when no valid session cookie."""
    app = FastAPI()
    app.include_router(artifacts_router.router)

    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.get("/api/threads/thread-1/artifacts/mnt/user-data/outputs/sample.skill/SKILL.md")
    assert resp.status_code == 401


def test_skill_archive_preview_rejects_oversized_member_before_decompression(tmp_path) -> None:
    skill_path = tmp_path / "sample.skill"
    payload = b"A" * (artifacts_router.MAX_SKILL_ARCHIVE_MEMBER_BYTES + 1)
    with zipfile.ZipFile(skill_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zip_ref:
        zip_ref.writestr("SKILL.md", payload)

    assert skill_path.stat().st_size < artifacts_router.MAX_SKILL_ARCHIVE_MEMBER_BYTES

    with pytest.raises(HTTPException) as exc_info:
        artifacts_router._extract_file_from_skill_archive(skill_path, "SKILL.md")

    assert exc_info.value.status_code == 413
