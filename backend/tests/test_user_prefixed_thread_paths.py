"""Tests for US-010: User-prefixed thread filesystem paths.

Verifies that:
- Paths exposes user-prefixed helpers for workspace, uploads, outputs, user-data root, and acp-workspace
- ensure_thread_dirs creates user-prefixed directories for authenticated runs
- resolve_virtual_path resolves /mnt/user-data paths under the authenticated user's prefix
- delete_thread_dir deletes only the authenticated user's prefixed thread directory
- The same thread_id under two different users maps to different host paths
"""

import pytest

from deerflow.config.paths import Paths

USER_A = "user-aaaa-1111"
USER_B = "user-bbbb-2222"
THREAD_ID = "thread-abc123"


# ---------------------------------------------------------------------------
# User-prefixed path helpers
# ---------------------------------------------------------------------------


class TestUserPrefixedPathHelpers:
    """Paths exposes user-prefixed helpers for all thread subdirectories."""

    def test_user_thread_dir(self, tmp_path):
        paths = Paths(base_dir=tmp_path)
        result = paths.user_thread_dir(USER_A, THREAD_ID)
        assert result == tmp_path / "users" / USER_A / "threads" / THREAD_ID

    def test_user_thread_workspace_dir(self, tmp_path):
        paths = Paths(base_dir=tmp_path)
        result = paths.user_thread_workspace_dir(USER_A, THREAD_ID)
        assert result == tmp_path / "users" / USER_A / "threads" / THREAD_ID / "workspace"

    def test_user_thread_uploads_dir(self, tmp_path):
        paths = Paths(base_dir=tmp_path)
        result = paths.user_thread_uploads_dir(USER_A, THREAD_ID)
        assert result == tmp_path / "users" / USER_A / "threads" / THREAD_ID / "uploads"

    def test_user_thread_outputs_dir(self, tmp_path):
        paths = Paths(base_dir=tmp_path)
        result = paths.user_thread_outputs_dir(USER_A, THREAD_ID)
        assert result == tmp_path / "users" / USER_A / "threads" / THREAD_ID / "outputs"

    def test_user_thread_acp_workspace_dir(self, tmp_path):
        paths = Paths(base_dir=tmp_path)
        result = paths.user_thread_acp_workspace_dir(USER_A, THREAD_ID)
        assert result == tmp_path / "users" / USER_A / "threads" / THREAD_ID / "acp-workspace"

    def test_same_thread_id_different_users_maps_to_different_paths(self, tmp_path):
        paths = Paths(base_dir=tmp_path)
        path_a = paths.user_thread_workspace_dir(USER_A, THREAD_ID)
        path_b = paths.user_thread_workspace_dir(USER_B, THREAD_ID)
        assert path_a != path_b
        assert USER_A in str(path_a)
        assert USER_B in str(path_b)


# ---------------------------------------------------------------------------
# ensure_thread_dirs with user_id
# ---------------------------------------------------------------------------


class TestEnsureThreadDirsUserPrefixed:
    """ensure_thread_dirs creates user-prefixed directories for authenticated runs."""

    def test_creates_user_prefixed_workspace(self, tmp_path):
        paths = Paths(base_dir=tmp_path)
        paths.ensure_thread_dirs(THREAD_ID, user_id=USER_A)
        assert (tmp_path / "users" / USER_A / "threads" / THREAD_ID / "workspace").exists()

    def test_creates_user_prefixed_uploads(self, tmp_path):
        paths = Paths(base_dir=tmp_path)
        paths.ensure_thread_dirs(THREAD_ID, user_id=USER_A)
        assert (tmp_path / "users" / USER_A / "threads" / THREAD_ID / "uploads").exists()

    def test_creates_user_prefixed_outputs(self, tmp_path):
        paths = Paths(base_dir=tmp_path)
        paths.ensure_thread_dirs(THREAD_ID, user_id=USER_A)
        assert (tmp_path / "users" / USER_A / "threads" / THREAD_ID / "outputs").exists()

    def test_creates_user_prefixed_acp_workspace(self, tmp_path):
        paths = Paths(base_dir=tmp_path)
        paths.ensure_thread_dirs(THREAD_ID, user_id=USER_A)
        assert (tmp_path / "users" / USER_A / "threads" / THREAD_ID / "acp-workspace").exists()

    def test_does_not_create_legacy_thread_dir_when_user_id_given(self, tmp_path):
        paths = Paths(base_dir=tmp_path)
        paths.ensure_thread_dirs(THREAD_ID, user_id=USER_A)
        # Legacy path should NOT be created
        assert not (tmp_path / "threads" / THREAD_ID).exists()

    def test_same_thread_id_two_users_creates_distinct_dirs(self, tmp_path):
        paths = Paths(base_dir=tmp_path)
        paths.ensure_thread_dirs(THREAD_ID, user_id=USER_A)
        paths.ensure_thread_dirs(THREAD_ID, user_id=USER_B)

        assert (tmp_path / "users" / USER_A / "threads" / THREAD_ID / "workspace").exists()
        assert (tmp_path / "users" / USER_B / "threads" / THREAD_ID / "workspace").exists()
        # Directories are distinct
        assert (tmp_path / "users" / USER_A / "threads" / THREAD_ID) != (tmp_path / "users" / USER_B / "threads" / THREAD_ID)


# ---------------------------------------------------------------------------
# resolve_virtual_path with user_id
# ---------------------------------------------------------------------------


class TestResolveVirtualPathUserPrefixed:
    """resolve_virtual_path resolves /mnt/user-data paths under the user's prefix."""

    def test_resolves_workspace_path_under_user_prefix(self, tmp_path):
        paths = Paths(base_dir=tmp_path)
        result = paths.resolve_virtual_path(THREAD_ID, "/mnt/user-data/workspace/file.txt", user_id=USER_A)
        expected_base = tmp_path / "users" / USER_A / "threads" / THREAD_ID
        assert str(result).startswith(str(expected_base))
        assert "file.txt" in str(result)

    def test_resolves_outputs_path_under_user_prefix(self, tmp_path):
        paths = Paths(base_dir=tmp_path)
        result = paths.resolve_virtual_path(THREAD_ID, "/mnt/user-data/outputs/report.pdf", user_id=USER_A)
        expected_base = tmp_path / "users" / USER_A / "threads" / THREAD_ID
        assert str(result).startswith(str(expected_base))

    def test_user_a_and_user_b_resolve_to_different_paths(self, tmp_path):
        paths = Paths(base_dir=tmp_path)
        path_a = paths.resolve_virtual_path(THREAD_ID, "/mnt/user-data/workspace/file.txt", user_id=USER_A)
        path_b = paths.resolve_virtual_path(THREAD_ID, "/mnt/user-data/workspace/file.txt", user_id=USER_B)
        assert path_a != path_b
        assert USER_A in str(path_a)
        assert USER_B in str(path_b)

    def test_rejects_path_traversal(self, tmp_path):
        paths = Paths(base_dir=tmp_path)
        with pytest.raises(ValueError, match="path traversal"):
            paths.resolve_virtual_path(THREAD_ID, "/mnt/user-data/../../../etc/passwd", user_id=USER_A)

    def test_rejects_path_without_virtual_prefix(self, tmp_path):
        paths = Paths(base_dir=tmp_path)
        with pytest.raises(ValueError):
            paths.resolve_virtual_path(THREAD_ID, "/etc/passwd", user_id=USER_A)


# ---------------------------------------------------------------------------
# delete_thread_dir with user_id
# ---------------------------------------------------------------------------


class TestDeleteThreadDirUserPrefixed:
    """delete_thread_dir deletes only the authenticated user's prefixed thread directory."""

    def test_deletes_user_prefixed_thread_dir(self, tmp_path):
        paths = Paths(base_dir=tmp_path)
        paths.ensure_thread_dirs(THREAD_ID, user_id=USER_A)
        assert (tmp_path / "users" / USER_A / "threads" / THREAD_ID).exists()

        paths.delete_thread_dir(THREAD_ID, user_id=USER_A)

        assert not (tmp_path / "users" / USER_A / "threads" / THREAD_ID).exists()

    def test_does_not_delete_other_users_thread_dir(self, tmp_path):
        paths = Paths(base_dir=tmp_path)
        paths.ensure_thread_dirs(THREAD_ID, user_id=USER_A)
        paths.ensure_thread_dirs(THREAD_ID, user_id=USER_B)

        paths.delete_thread_dir(THREAD_ID, user_id=USER_A)

        # User B's directory must still exist
        assert (tmp_path / "users" / USER_B / "threads" / THREAD_ID).exists()

    def test_idempotent_when_dir_missing(self, tmp_path):
        paths = Paths(base_dir=tmp_path)
        # Should not raise even if directory doesn't exist
        paths.delete_thread_dir(THREAD_ID, user_id=USER_A)
