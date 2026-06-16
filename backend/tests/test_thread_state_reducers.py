"""Tests for ThreadState reducers."""

from __future__ import annotations

from typing import get_type_hints

import pytest

from deerflow.agents.thread_state import ThreadState, merge_artifacts, merge_promoted, merge_sandbox, merge_viewed_images


def test_merge_sandbox_none_new_preserves_existing() -> None:
    existing = {"sandbox_id": "sandbox-1"}

    assert merge_sandbox(existing, None) == existing


def test_merge_sandbox_none_existing_accepts_new() -> None:
    new = {"sandbox_id": "sandbox-1"}

    assert merge_sandbox(None, new) == new


def test_merge_sandbox_same_id_is_idempotent() -> None:
    existing = {"sandbox_id": "sandbox-1"}
    new = {"sandbox_id": "sandbox-1"}

    assert merge_sandbox(existing, new) == existing


def test_merge_sandbox_conflicting_ids_raise() -> None:
    with pytest.raises(ValueError, match="Conflicting sandbox state updates"):
        merge_sandbox({"sandbox_id": "sandbox-1"}, {"sandbox_id": "sandbox-2"})


def test_thread_state_reducer_annotations_are_wired() -> None:
    hints = get_type_hints(ThreadState, include_extras=True)

    assert merge_sandbox in hints["sandbox"].__metadata__
    assert merge_artifacts in hints["artifacts"].__metadata__
    assert merge_viewed_images in hints["viewed_images"].__metadata__
    assert merge_promoted in hints["promoted"].__metadata__


def test_merge_promoted_preserves_existing_when_new_is_none() -> None:
    existing = {"catalog_hash": "abc", "names": ["search"]}

    assert merge_promoted(existing, None) is existing


def test_merge_promoted_deduplicates_new_names() -> None:
    assert merge_promoted(None, {"catalog_hash": "abc", "names": ["search", "search", "fetch"]}) == {
        "catalog_hash": "abc",
        "names": ["search", "fetch"],
    }


def test_merge_promoted_replaces_when_catalog_hash_changes() -> None:
    existing = {"catalog_hash": "abc", "names": ["old"]}

    assert merge_promoted(existing, {"catalog_hash": "def", "names": ["new", "new", "old"]}) == {
        "catalog_hash": "def",
        "names": ["new", "old"],
    }


def test_merge_promoted_unions_names_when_catalog_hash_matches() -> None:
    existing = {"catalog_hash": "abc", "names": ["search", "fetch"]}

    assert merge_promoted(existing, {"catalog_hash": "abc", "names": ["fetch", "scrape"]}) == {
        "catalog_hash": "abc",
        "names": ["search", "fetch", "scrape"],
    }
