"""Tests for memory token counting and tiktoken cache behavior."""

from __future__ import annotations

import threading
from unittest import mock

import pytest
from pydantic import ValidationError

from deerflow.agents.memory import prompt as prompt_module
from deerflow.agents.memory.prompt import (
    _count_tokens,
    _get_tiktoken_encoding,
    _tiktoken_encoding_cache,
    format_memory_for_injection,
    warm_tiktoken_cache,
)
from deerflow.config.memory_config import MemoryConfig


def test_get_tiktoken_encoding_returns_none_when_unavailable(monkeypatch):
    monkeypatch.setattr(prompt_module, "TIKTOKEN_AVAILABLE", False)

    assert _get_tiktoken_encoding("cl100k_base") is None


def test_get_tiktoken_encoding_populates_cache(monkeypatch):
    _tiktoken_encoding_cache.pop("cl100k_base", None)
    fake_encoding = mock.Mock()
    monkeypatch.setattr(prompt_module.tiktoken, "get_encoding", mock.Mock(return_value=fake_encoding))

    assert _get_tiktoken_encoding("cl100k_base") is fake_encoding
    assert _tiktoken_encoding_cache["cl100k_base"] is fake_encoding


def test_get_tiktoken_encoding_uses_cached_value(monkeypatch):
    fake_encoding = mock.Mock()
    monkeypatch.setitem(_tiktoken_encoding_cache, "cl100k_base", fake_encoding)
    get_encoding = mock.Mock(side_effect=AssertionError("get_encoding must not be called"))
    monkeypatch.setattr(prompt_module.tiktoken, "get_encoding", get_encoding)

    assert _get_tiktoken_encoding("cl100k_base") is fake_encoding
    get_encoding.assert_not_called()


def test_get_tiktoken_encoding_caches_failure(monkeypatch):
    _tiktoken_encoding_cache.pop("bogus_encoding", None)
    get_encoding = mock.Mock(side_effect=OSError("download failed"))
    monkeypatch.setattr(prompt_module.tiktoken, "get_encoding", get_encoding)

    assert _get_tiktoken_encoding("bogus_encoding") is None
    assert _get_tiktoken_encoding("bogus_encoding") is None
    assert get_encoding.call_count == 1

    cached = _tiktoken_encoding_cache["bogus_encoding"]
    assert isinstance(cached, tuple)
    assert cached[0] is None
    _tiktoken_encoding_cache.pop("bogus_encoding", None)


def test_get_tiktoken_encoding_retries_after_cooldown(monkeypatch):
    _tiktoken_encoding_cache.pop("flaky_encoding", None)
    fake_encoding = mock.Mock()
    get_encoding = mock.Mock(side_effect=[OSError("transient outage"), fake_encoding])
    monkeypatch.setattr(prompt_module.tiktoken, "get_encoding", get_encoding)

    assert _get_tiktoken_encoding("flaky_encoding") is None
    _none_value, failed_at = _tiktoken_encoding_cache["flaky_encoding"]
    _tiktoken_encoding_cache["flaky_encoding"] = (
        None,
        failed_at - prompt_module._TIKTOKEN_RETRY_COOLDOWN_S - 1,
    )

    assert _get_tiktoken_encoding("flaky_encoding") is fake_encoding
    assert get_encoding.call_count == 2
    _tiktoken_encoding_cache.pop("flaky_encoding", None)


def test_in_flight_tiktoken_load_returns_none_without_duplicate_download(monkeypatch):
    _tiktoken_encoding_cache.pop("slow_encoding", None)
    started = threading.Event()
    release = threading.Event()
    fake_encoding = mock.Mock()

    def slow_get_encoding(_name):
        started.set()
        assert release.wait(timeout=2), "timed out waiting to release get_encoding"
        return fake_encoding

    get_encoding = mock.Mock(side_effect=slow_get_encoding)
    monkeypatch.setattr(prompt_module.tiktoken, "get_encoding", get_encoding)
    result: dict[str, object | None] = {}

    def load_encoding():
        result["encoding"] = _get_tiktoken_encoding("slow_encoding")

    thread = threading.Thread(target=load_encoding)
    thread.start()
    try:
        assert started.wait(timeout=1), "slow get_encoding did not start"
        assert _get_tiktoken_encoding("slow_encoding") is None
        assert get_encoding.call_count == 1
    finally:
        release.set()
        thread.join(timeout=2)
        _tiktoken_encoding_cache.pop("slow_encoding", None)

    assert result["encoding"] is fake_encoding


def test_count_tokens_falls_back_when_tiktoken_unavailable(monkeypatch):
    monkeypatch.setattr(prompt_module, "TIKTOKEN_AVAILABLE", False)
    text = "Some text to count"

    assert _count_tokens(text) == len(text) // 4


def test_count_tokens_use_tiktoken_false_never_touches_tiktoken(monkeypatch):
    loader = mock.Mock(side_effect=AssertionError("_get_tiktoken_encoding must not be called"))
    monkeypatch.setattr(prompt_module, "_get_tiktoken_encoding", loader)

    text = "Hello, world! This is a network-free count."

    assert _count_tokens(text, use_tiktoken=False) == len(text) // 4
    loader.assert_not_called()


def test_cjk_char_estimate_is_denser_than_plain_quarter(monkeypatch):
    monkeypatch.setattr(prompt_module, "TIKTOKEN_AVAILABLE", False)
    text = "用户偏好简洁的中文回答并关注金融领域"

    result = _count_tokens(text)

    assert result == len(text) // 2
    assert result > len(text) // 4


def test_format_memory_use_tiktoken_false_never_touches_tiktoken(monkeypatch):
    loader = mock.Mock(side_effect=AssertionError("_get_tiktoken_encoding must not be called"))
    monkeypatch.setattr(prompt_module, "_get_tiktoken_encoding", loader)
    memory_data = {
        "facts": [
            {"content": "User prefers concise answers.", "category": "preference", "confidence": 0.9},
            {"content": "User works with LangGraph.", "category": "knowledge", "confidence": 0.8},
        ]
    }

    result = format_memory_for_injection(memory_data, max_tokens=2000, use_tiktoken=False)

    assert "User prefers concise answers." in result
    loader.assert_not_called()


def test_format_memory_use_tiktoken_true_uses_encoding(monkeypatch):
    fake_encoding = mock.Mock()
    fake_encoding.encode.side_effect = lambda text: list(range(len(text)))
    loader = mock.Mock(return_value=fake_encoding)
    monkeypatch.setattr(prompt_module, "_get_tiktoken_encoding", loader)
    memory_data = {
        "facts": [
            {"content": "User prefers concise answers.", "category": "preference", "confidence": 0.9},
        ]
    }

    result = format_memory_for_injection(memory_data, max_tokens=2000, use_tiktoken=True)

    assert "User prefers concise answers." in result
    assert fake_encoding.encode.called


def test_warm_tiktoken_cache_returns_true_when_encoding_available(monkeypatch):
    _tiktoken_encoding_cache.pop("cl100k_base", None)
    fake_encoding = mock.Mock()
    monkeypatch.setattr(prompt_module.tiktoken, "get_encoding", mock.Mock(return_value=fake_encoding))

    assert warm_tiktoken_cache() is True


def test_memory_config_token_counting_defaults_and_validation():
    assert MemoryConfig().token_counting == "tiktoken"
    assert MemoryConfig(token_counting="char").token_counting == "char"
    with pytest.raises(ValidationError):
        MemoryConfig(token_counting="invalid")
