"""Tests for canonical user resource prefix helpers in app.gateway.user_prefix.

Covers:
- validate_user_id: valid IDs, empty, path traversal, slashes, backslashes, unsafe chars
- user_threads_namespace: correct tuple structure
- user_thread_owners_namespace: correct tuple structure
- user_memory_namespace: correct tuple structure
- user_extensions_namespace: correct tuple structure
- validated_user_id_for_path: delegates to validate_user_id
- Stable filesystem-safe mapping (same input → same output)
- Two different user IDs produce different namespaces
"""

from __future__ import annotations

import pytest

from app.gateway.user_prefix import (
    user_extensions_namespace,
    user_memory_namespace,
    user_thread_owners_namespace,
    user_threads_namespace,
    validate_user_id,
    validated_user_id_for_path,
)

# ---------------------------------------------------------------------------
# validate_user_id
# ---------------------------------------------------------------------------


class TestValidateUserId:
    def test_valid_uuid_style_id(self):
        uid = "12345678-1234-5678-1234-567812345678"
        assert validate_user_id(uid) == uid

    def test_valid_alphanumeric(self):
        assert validate_user_id("abc123") == "abc123"

    def test_valid_with_underscores(self):
        assert validate_user_id("user_abc_123") == "user_abc_123"

    def test_valid_with_hyphens(self):
        assert validate_user_id("user-abc-123") == "user-abc-123"

    def test_empty_string_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            validate_user_id("")

    def test_forward_slash_raises(self):
        with pytest.raises(ValueError, match="path separators"):
            validate_user_id("user/id")

    def test_backslash_raises(self):
        with pytest.raises(ValueError, match="path separators"):
            validate_user_id("user\\id")

    def test_dot_dot_traversal_raises(self):
        with pytest.raises(ValueError):
            validate_user_id("../etc/passwd")

    def test_space_raises(self):
        with pytest.raises(ValueError, match="unsafe characters"):
            validate_user_id("user id")

    def test_colon_raises(self):
        with pytest.raises(ValueError, match="unsafe characters"):
            validate_user_id("user:id")

    def test_at_sign_raises(self):
        with pytest.raises(ValueError, match="unsafe characters"):
            validate_user_id("user@domain")

    def test_null_byte_raises(self):
        with pytest.raises(ValueError, match="unsafe characters"):
            validate_user_id("user\x00id")


# ---------------------------------------------------------------------------
# Namespace helpers
# ---------------------------------------------------------------------------


class TestUserThreadsNamespace:
    def test_returns_tuple(self):
        ns = user_threads_namespace("abc-123")
        assert isinstance(ns, tuple)

    def test_starts_with_threads(self):
        ns = user_threads_namespace("abc-123")
        assert ns[0] == "threads"

    def test_encodes_user_id(self):
        ns = user_threads_namespace("abc-123")
        assert "abc-123" in ns[-1]

    def test_two_users_produce_different_namespaces(self):
        ns_a = user_threads_namespace("user-a")
        ns_b = user_threads_namespace("user-b")
        assert ns_a != ns_b

    def test_stable_output(self):
        assert user_threads_namespace("abc") == user_threads_namespace("abc")

    def test_invalid_user_id_raises(self):
        with pytest.raises(ValueError):
            user_threads_namespace("")


class TestUserThreadOwnersNamespace:
    def test_returns_tuple(self):
        ns = user_thread_owners_namespace("abc-123")
        assert isinstance(ns, tuple)

    def test_starts_with_thread_owners(self):
        ns = user_thread_owners_namespace("abc-123")
        assert ns[0] == "thread_owners"

    def test_encodes_user_id(self):
        ns = user_thread_owners_namespace("abc-123")
        assert "abc-123" in ns[-1]

    def test_two_users_produce_different_namespaces(self):
        assert user_thread_owners_namespace("user-a") != user_thread_owners_namespace("user-b")

    def test_stable_output(self):
        assert user_thread_owners_namespace("abc") == user_thread_owners_namespace("abc")


class TestUserMemoryNamespace:
    def test_returns_tuple(self):
        ns = user_memory_namespace("abc-123")
        assert isinstance(ns, tuple)

    def test_starts_with_memory(self):
        ns = user_memory_namespace("abc-123")
        assert ns[0] == "memory"

    def test_encodes_user_id(self):
        ns = user_memory_namespace("abc-123")
        assert "abc-123" in ns[-1]

    def test_two_users_produce_different_namespaces(self):
        assert user_memory_namespace("user-a") != user_memory_namespace("user-b")


class TestUserExtensionsNamespace:
    def test_returns_tuple(self):
        ns = user_extensions_namespace("abc-123")
        assert isinstance(ns, tuple)

    def test_starts_with_extensions_config(self):
        ns = user_extensions_namespace("abc-123")
        assert ns[0] == "extensions_config"

    def test_encodes_user_id(self):
        ns = user_extensions_namespace("abc-123")
        assert "abc-123" in ns[-1]

    def test_two_users_produce_different_namespaces(self):
        assert user_extensions_namespace("user-a") != user_extensions_namespace("user-b")


# ---------------------------------------------------------------------------
# Cross-resource namespace isolation
# ---------------------------------------------------------------------------


def test_different_resource_types_produce_different_namespaces():
    uid = "same-user"
    namespaces = [
        user_threads_namespace(uid),
        user_thread_owners_namespace(uid),
        user_memory_namespace(uid),
        user_extensions_namespace(uid),
    ]
    assert len(set(namespaces)) == len(namespaces), "Each resource type must have a unique namespace"


# ---------------------------------------------------------------------------
# validated_user_id_for_path
# ---------------------------------------------------------------------------


class TestValidatedUserIdForPath:
    def test_returns_valid_id_unchanged(self):
        uid = "abc-123"
        assert validated_user_id_for_path(uid) == uid

    def test_rejects_empty(self):
        with pytest.raises(ValueError):
            validated_user_id_for_path("")

    def test_rejects_slash(self):
        with pytest.raises(ValueError):
            validated_user_id_for_path("a/b")

    def test_rejects_backslash(self):
        with pytest.raises(ValueError):
            validated_user_id_for_path("a\\b")

    def test_rejects_unsafe_chars(self):
        with pytest.raises(ValueError):
            validated_user_id_for_path("user@host")
