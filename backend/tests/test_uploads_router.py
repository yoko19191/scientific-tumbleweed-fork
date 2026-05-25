import asyncio
import os
import stat
from io import BytesIO
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import UploadFile

from app.gateway.routers import uploads

USER_A = "user-aaaa-1111"
USER_B = "user-bbbb-2222"


def _mock_request(user_id: str | None = None) -> MagicMock:
    """Return a minimal mock Request with optional auth state."""
    request = MagicMock()
    if user_id is not None:
        request.state.auth.user.id = user_id
    else:
        request.state.auth = None
    return request


def _patch_require_owner(user_id: str = USER_A):
    """Patch require_thread_owner to return user_id without hitting the store."""
    return patch.object(uploads, "require_thread_owner", new=AsyncMock(return_value=user_id))


def test_upload_files_writes_thread_storage_and_skips_local_sandbox_sync(tmp_path):
    thread_uploads_dir = tmp_path / "uploads"
    thread_uploads_dir.mkdir(parents=True)

    provider = MagicMock()
    provider.uses_thread_data_mounts = True
    provider.acquire.return_value = "local"
    sandbox = MagicMock()
    provider.get.return_value = sandbox

    with (
        _patch_require_owner(),
        patch.object(uploads, "get_uploads_dir", return_value=thread_uploads_dir),
        patch.object(uploads, "ensure_uploads_dir", return_value=thread_uploads_dir),
        patch.object(uploads, "get_sandbox_provider", return_value=provider),
    ):
        file = UploadFile(filename="notes.txt", file=BytesIO(b"hello uploads"))
        result = asyncio.run(uploads.upload_files("thread-local", _mock_request(), files=[file]))

    assert result.success is True
    assert len(result.files) == 1
    assert result.files[0]["filename"] == "notes.txt"
    assert (thread_uploads_dir / "notes.txt").read_bytes() == b"hello uploads"

    sandbox.update_file.assert_not_called()


def test_upload_files_auto_renames_duplicate_form_filenames(tmp_path):
    thread_uploads_dir = tmp_path / "uploads"
    thread_uploads_dir.mkdir(parents=True)

    provider = MagicMock()
    provider.uses_thread_data_mounts = True

    with (
        _patch_require_owner(),
        patch.object(uploads, "get_uploads_dir", return_value=thread_uploads_dir),
        patch.object(uploads, "ensure_uploads_dir", return_value=thread_uploads_dir),
        patch.object(uploads, "get_sandbox_provider", return_value=provider),
    ):
        result = asyncio.run(
            uploads.upload_files(
                "thread-local",
                _mock_request(),
                files=[
                    UploadFile(filename="data.txt", file=BytesIO(b"first")),
                    UploadFile(filename="data.txt", file=BytesIO(b"second")),
                ],
            )
        )

    assert result.success is True
    assert [file_info["filename"] for file_info in result.files] == ["data.txt", "data_1.txt"]
    assert "original_filename" not in result.files[0]
    assert result.files[1]["original_filename"] == "data.txt"
    assert (thread_uploads_dir / "data.txt").read_bytes() == b"first"
    assert (thread_uploads_dir / "data_1.txt").read_bytes() == b"second"


def test_upload_files_skips_acquire_when_thread_data_is_mounted(tmp_path):
    thread_uploads_dir = tmp_path / "uploads"
    thread_uploads_dir.mkdir(parents=True)

    provider = MagicMock()
    provider.uses_thread_data_mounts = True

    with (
        _patch_require_owner(),
        patch.object(uploads, "get_uploads_dir", return_value=thread_uploads_dir),
        patch.object(uploads, "ensure_uploads_dir", return_value=thread_uploads_dir),
        patch.object(uploads, "get_sandbox_provider", return_value=provider),
    ):
        file = UploadFile(filename="notes.txt", file=BytesIO(b"hello uploads"))
        result = asyncio.run(uploads.upload_files("thread-mounted", _mock_request(), files=[file]))

    assert result.success is True
    assert (thread_uploads_dir / "notes.txt").read_bytes() == b"hello uploads"
    provider.acquire.assert_not_called()
    provider.get.assert_not_called()


def test_upload_files_does_not_auto_convert_documents_by_default(tmp_path):
    thread_uploads_dir = tmp_path / "uploads"
    thread_uploads_dir.mkdir(parents=True)

    provider = MagicMock()
    provider.uses_thread_data_mounts = True
    provider.acquire.return_value = "local"
    sandbox = MagicMock()
    provider.get.return_value = sandbox

    with (
        _patch_require_owner(),
        patch.object(uploads, "get_uploads_dir", return_value=thread_uploads_dir),
        patch.object(uploads, "ensure_uploads_dir", return_value=thread_uploads_dir),
        patch.object(uploads, "get_sandbox_provider", return_value=provider),
        patch.object(uploads, "_auto_convert_documents_enabled", return_value=False),
        patch.object(uploads, "convert_file_to_markdown", AsyncMock()) as convert_mock,
    ):
        file = UploadFile(filename="report.pdf", file=BytesIO(b"pdf-bytes"))
        result = asyncio.run(uploads.upload_files("thread-local", _mock_request(), files=[file]))

    assert result.success is True
    assert len(result.files) == 1
    assert result.files[0]["filename"] == "report.pdf"
    assert "markdown_file" not in result.files[0]
    convert_mock.assert_not_called()
    assert not (thread_uploads_dir / "report.md").exists()


def test_upload_files_syncs_non_local_sandbox_and_marks_markdown_file(tmp_path):
    thread_uploads_dir = tmp_path / "uploads"
    thread_uploads_dir.mkdir(parents=True)

    provider = MagicMock()
    provider.uses_thread_data_mounts = False
    provider.acquire.return_value = "aio-1"
    sandbox = MagicMock()
    provider.get.return_value = sandbox

    async def fake_convert(file_path: Path) -> Path:
        md_path = file_path.with_suffix(".md")
        md_path.write_text("converted", encoding="utf-8")
        return md_path

    with (
        _patch_require_owner(),
        patch.object(uploads, "get_uploads_dir", return_value=thread_uploads_dir),
        patch.object(uploads, "ensure_uploads_dir", return_value=thread_uploads_dir),
        patch.object(uploads, "get_sandbox_provider", return_value=provider),
        patch.object(uploads, "_auto_convert_documents_enabled", return_value=True),
        patch.object(uploads, "convert_file_to_markdown", AsyncMock(side_effect=fake_convert)),
    ):
        file = UploadFile(filename="report.pdf", file=BytesIO(b"pdf-bytes"))
        result = asyncio.run(uploads.upload_files("thread-aio", _mock_request(), files=[file]))

    assert result.success is True
    assert len(result.files) == 1
    file_info = result.files[0]
    assert file_info["filename"] == "report.pdf"
    assert file_info["markdown_file"] == "report.md"

    assert (thread_uploads_dir / "report.pdf").read_bytes() == b"pdf-bytes"
    assert (thread_uploads_dir / "report.md").read_text(encoding="utf-8") == "converted"

    sandbox.update_file.assert_any_call("/mnt/user-data/uploads/report.pdf", b"pdf-bytes")
    sandbox.update_file.assert_any_call("/mnt/user-data/uploads/report.md", b"converted")


def test_upload_files_makes_non_local_files_sandbox_writable(tmp_path):
    thread_uploads_dir = tmp_path / "uploads"
    thread_uploads_dir.mkdir(parents=True)

    provider = MagicMock()
    provider.uses_thread_data_mounts = False
    provider.acquire.return_value = "aio-1"
    sandbox = MagicMock()
    provider.get.return_value = sandbox

    async def fake_convert(file_path: Path) -> Path:
        md_path = file_path.with_suffix(".md")
        md_path.write_text("converted", encoding="utf-8")
        return md_path

    with (
        _patch_require_owner(),
        patch.object(uploads, "get_uploads_dir", return_value=thread_uploads_dir),
        patch.object(uploads, "ensure_uploads_dir", return_value=thread_uploads_dir),
        patch.object(uploads, "get_sandbox_provider", return_value=provider),
        patch.object(uploads, "_auto_convert_documents_enabled", return_value=True),
        patch.object(uploads, "convert_file_to_markdown", AsyncMock(side_effect=fake_convert)),
        patch.object(uploads, "_make_file_sandbox_writable") as make_writable,
    ):
        file = UploadFile(filename="report.pdf", file=BytesIO(b"pdf-bytes"))
        result = asyncio.run(uploads.upload_files("thread-aio", _mock_request(), files=[file]))

    assert result.success is True
    make_writable.assert_any_call(thread_uploads_dir / "report.pdf")
    make_writable.assert_any_call(thread_uploads_dir / "report.md")


def test_upload_files_does_not_adjust_permissions_for_local_sandbox(tmp_path):
    thread_uploads_dir = tmp_path / "uploads"
    thread_uploads_dir.mkdir(parents=True)

    provider = MagicMock()
    provider.uses_thread_data_mounts = True
    provider.acquire.return_value = "local"
    sandbox = MagicMock()
    provider.get.return_value = sandbox

    with (
        _patch_require_owner(),
        patch.object(uploads, "get_uploads_dir", return_value=thread_uploads_dir),
        patch.object(uploads, "ensure_uploads_dir", return_value=thread_uploads_dir),
        patch.object(uploads, "get_sandbox_provider", return_value=provider),
        patch.object(uploads, "_make_file_sandbox_writable") as make_writable,
    ):
        file = UploadFile(filename="notes.txt", file=BytesIO(b"hello uploads"))
        result = asyncio.run(uploads.upload_files("thread-local", _mock_request(), files=[file]))

    assert result.success is True
    make_writable.assert_not_called()


def test_make_file_sandbox_writable_adds_write_bits_for_regular_files(tmp_path):
    file_path = tmp_path / "report.pdf"
    file_path.write_bytes(b"pdf-bytes")
    os_chmod_mode = stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH
    file_path.chmod(os_chmod_mode)

    uploads._make_file_sandbox_writable(file_path)

    updated_mode = stat.S_IMODE(file_path.stat().st_mode)
    assert updated_mode & stat.S_IWUSR
    assert updated_mode & stat.S_IWGRP
    assert updated_mode & stat.S_IWOTH


def test_make_file_sandbox_writable_skips_symlinks(tmp_path):
    file_path = tmp_path / "target-link.txt"
    file_path.write_text("hello", encoding="utf-8")
    symlink_stat = MagicMock(st_mode=stat.S_IFLNK)

    with (
        patch.object(uploads.os, "lstat", return_value=symlink_stat),
        patch.object(uploads.os, "chmod") as chmod,
    ):
        uploads._make_file_sandbox_writable(file_path)

    chmod.assert_not_called()


def test_upload_files_rejects_dotdot_and_dot_filenames(tmp_path):
    thread_uploads_dir = tmp_path / "uploads"
    thread_uploads_dir.mkdir(parents=True)

    provider = MagicMock()
    provider.acquire.return_value = "local"
    sandbox = MagicMock()
    provider.get.return_value = sandbox

    with (
        _patch_require_owner(),
        patch.object(uploads, "get_uploads_dir", return_value=thread_uploads_dir),
        patch.object(uploads, "ensure_uploads_dir", return_value=thread_uploads_dir),
        patch.object(uploads, "get_sandbox_provider", return_value=provider),
    ):
        # These filenames must be rejected outright
        for bad_name in ["..", "."]:
            file = UploadFile(filename=bad_name, file=BytesIO(b"data"))
            result = asyncio.run(uploads.upload_files("thread-local", _mock_request(), files=[file]))
            assert result.success is True
            assert result.files == [], f"Expected no files for unsafe filename {bad_name!r}"

        # Path-traversal prefixes are stripped to the basename and accepted safely
        file = UploadFile(filename="../etc/passwd", file=BytesIO(b"data"))
        result = asyncio.run(uploads.upload_files("thread-local", _mock_request(), files=[file]))
        assert result.success is True
        assert len(result.files) == 1
        assert result.files[0]["filename"] == "passwd"

    # Only the safely normalised file should exist
    assert [f.name for f in thread_uploads_dir.iterdir()] == ["passwd"]


def test_upload_files_rejects_preexisting_symlink_destination(tmp_path):
    thread_uploads_dir = tmp_path / "uploads"
    thread_uploads_dir.mkdir(parents=True)
    outside_file = tmp_path / "outside.txt"
    outside_file.write_text("protected", encoding="utf-8")
    (thread_uploads_dir / "victim.txt").symlink_to(outside_file)

    provider = MagicMock()
    provider.uses_thread_data_mounts = True

    with (
        _patch_require_owner(),
        patch.object(uploads, "get_uploads_dir", return_value=thread_uploads_dir),
        patch.object(uploads, "ensure_uploads_dir", return_value=thread_uploads_dir),
        patch.object(uploads, "get_sandbox_provider", return_value=provider),
    ):
        file = UploadFile(filename="victim.txt", file=BytesIO(b"attacker upload"))
        result = asyncio.run(uploads.upload_files("thread-local", _mock_request(), files=[file]))

    assert result.success is False
    assert result.files == []
    assert result.skipped_files == ["victim.txt"]
    assert "skipped 1 unsafe file" in result.message
    assert outside_file.read_text(encoding="utf-8") == "protected"
    assert (thread_uploads_dir / "victim.txt").is_symlink()


def test_upload_files_rejects_dangling_symlink_destination(tmp_path):
    thread_uploads_dir = tmp_path / "uploads"
    thread_uploads_dir.mkdir(parents=True)
    missing_target = tmp_path / "missing-target.txt"
    (thread_uploads_dir / "victim.txt").symlink_to(missing_target)

    provider = MagicMock()
    provider.uses_thread_data_mounts = True

    with (
        _patch_require_owner(),
        patch.object(uploads, "get_uploads_dir", return_value=thread_uploads_dir),
        patch.object(uploads, "ensure_uploads_dir", return_value=thread_uploads_dir),
        patch.object(uploads, "get_sandbox_provider", return_value=provider),
    ):
        file = UploadFile(filename="victim.txt", file=BytesIO(b"attacker upload"))
        result = asyncio.run(uploads.upload_files("thread-local", _mock_request(), files=[file]))

    assert result.success is False
    assert result.files == []
    assert result.skipped_files == ["victim.txt"]
    assert not missing_target.exists()
    assert (thread_uploads_dir / "victim.txt").is_symlink()


def test_upload_files_rejects_hardlinked_destination_without_truncating(tmp_path):
    thread_uploads_dir = tmp_path / "uploads"
    thread_uploads_dir.mkdir(parents=True)
    outside_file = tmp_path / "outside.txt"
    outside_file.write_text("protected", encoding="utf-8")
    os.link(outside_file, thread_uploads_dir / "victim.txt")

    provider = MagicMock()
    provider.uses_thread_data_mounts = True

    with (
        _patch_require_owner(),
        patch.object(uploads, "get_uploads_dir", return_value=thread_uploads_dir),
        patch.object(uploads, "ensure_uploads_dir", return_value=thread_uploads_dir),
        patch.object(uploads, "get_sandbox_provider", return_value=provider),
    ):
        file = UploadFile(filename="victim.txt", file=BytesIO(b"attacker upload"))
        result = asyncio.run(uploads.upload_files("thread-local", _mock_request(), files=[file]))

    assert result.success is False
    assert result.files == []
    assert result.skipped_files == ["victim.txt"]
    assert outside_file.read_text(encoding="utf-8") == "protected"
    assert (thread_uploads_dir / "victim.txt").read_text(encoding="utf-8") == "protected"


def test_upload_files_overwrites_existing_regular_file(tmp_path):
    thread_uploads_dir = tmp_path / "uploads"
    thread_uploads_dir.mkdir(parents=True)
    existing_file = thread_uploads_dir / "notes.txt"
    existing_file.write_bytes(b"old upload")
    assert existing_file.stat().st_nlink == 1

    provider = MagicMock()
    provider.uses_thread_data_mounts = True

    with (
        _patch_require_owner(),
        patch.object(uploads, "get_uploads_dir", return_value=thread_uploads_dir),
        patch.object(uploads, "ensure_uploads_dir", return_value=thread_uploads_dir),
        patch.object(uploads, "get_sandbox_provider", return_value=provider),
    ):
        file = UploadFile(filename="notes.txt", file=BytesIO(b"new upload"))
        result = asyncio.run(uploads.upload_files("thread-local", _mock_request(), files=[file]))

    assert result.success is True
    assert [file_info["filename"] for file_info in result.files] == ["notes.txt"]
    assert existing_file.read_bytes() == b"new upload"
    assert existing_file.stat().st_nlink == 1


def test_delete_uploaded_file_removes_generated_markdown_companion(tmp_path):
    thread_uploads_dir = tmp_path / "uploads"
    thread_uploads_dir.mkdir(parents=True)
    (thread_uploads_dir / "report.pdf").write_bytes(b"pdf-bytes")
    (thread_uploads_dir / "report.md").write_text("converted", encoding="utf-8")

    with (
        _patch_require_owner(),
        patch.object(uploads, "get_uploads_dir", return_value=thread_uploads_dir),
    ):
        result = asyncio.run(uploads.delete_uploaded_file("thread-aio", "report.pdf", _mock_request()))

    assert result == {"success": True, "message": "Deleted report.pdf"}
    assert not (thread_uploads_dir / "report.pdf").exists()
    assert not (thread_uploads_dir / "report.md").exists()


# ---------------------------------------------------------------------------
# US-012: Cross-user access denial tests
# ---------------------------------------------------------------------------


def test_upload_returns_401_when_unauthenticated(tmp_path):
    """Upload endpoint must return 401 when no valid session cookie."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.gateway.routers import uploads as uploads_router

    app = FastAPI()
    app.include_router(uploads_router.router)

    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.post(
            "/api/threads/thread-1/uploads",
            files={"files": ("test.txt", b"hello", "text/plain")},
        )
    assert resp.status_code == 401


def test_list_uploads_returns_401_when_unauthenticated():
    """List uploads endpoint must return 401 when no valid session cookie."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.gateway.routers import uploads as uploads_router

    app = FastAPI()
    app.include_router(uploads_router.router)

    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.get("/api/threads/thread-1/uploads/list")
    assert resp.status_code == 401


def test_delete_upload_returns_401_when_unauthenticated():
    """Delete upload endpoint must return 401 when no valid session cookie."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.gateway.routers import uploads as uploads_router

    app = FastAPI()
    app.include_router(uploads_router.router)

    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.delete("/api/threads/thread-1/uploads/file.txt")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Auto-convert documents config tests
# ---------------------------------------------------------------------------


def test_auto_convert_documents_enabled_defaults_to_false_on_config_errors():
    with patch.object(uploads, "get_app_config", side_effect=RuntimeError("boom")):
        assert uploads._auto_convert_documents_enabled() is False


def test_auto_convert_documents_enabled_reads_dict_backed_uploads_config():
    cfg = MagicMock()
    cfg.uploads = {"auto_convert_documents": True}

    with patch.object(uploads, "get_app_config", return_value=cfg):
        assert uploads._auto_convert_documents_enabled() is True


def test_auto_convert_documents_enabled_accepts_boolean_and_string_truthy_values():
    false_cfg = MagicMock()
    false_cfg.uploads = MagicMock(auto_convert_documents=False)

    true_cfg = MagicMock()
    true_cfg.uploads = MagicMock(auto_convert_documents=True)

    string_true_cfg = MagicMock()
    string_true_cfg.uploads = MagicMock(auto_convert_documents="YES")

    string_false_cfg = MagicMock()
    string_false_cfg.uploads = MagicMock(auto_convert_documents="false")

    with patch.object(uploads, "get_app_config", return_value=false_cfg):
        assert uploads._auto_convert_documents_enabled() is False
    with patch.object(uploads, "get_app_config", return_value=true_cfg):
        assert uploads._auto_convert_documents_enabled() is True
    with patch.object(uploads, "get_app_config", return_value=string_true_cfg):
        assert uploads._auto_convert_documents_enabled() is True
    with patch.object(uploads, "get_app_config", return_value=string_false_cfg):
        assert uploads._auto_convert_documents_enabled() is False
