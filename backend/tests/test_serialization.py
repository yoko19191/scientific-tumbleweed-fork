"""Tests for deerflow.runtime.serialization."""

from __future__ import annotations


class _FakePydanticV2:
    """Object with model_dump (Pydantic v2)."""

    def model_dump(self):
        return {"key": "v2"}


class _FakePydanticV1:
    """Object with dict (Pydantic v1)."""

    def dict(self):
        return {"key": "v1"}


class _Unprintable:
    """Object whose str() raises."""

    def __str__(self):
        raise RuntimeError("no str")

    def __repr__(self):
        return "<Unprintable>"


def test_serialize_none():
    from deerflow.runtime.serialization import serialize_lc_object

    assert serialize_lc_object(None) is None


def test_serialize_primitives():
    from deerflow.runtime.serialization import serialize_lc_object

    assert serialize_lc_object("hello") == "hello"
    assert serialize_lc_object(42) == 42
    assert serialize_lc_object(3.14) == 3.14
    assert serialize_lc_object(True) is True


def test_serialize_dict():
    from deerflow.runtime.serialization import serialize_lc_object

    obj = {"a": _FakePydanticV2(), "b": [1, "two"]}
    result = serialize_lc_object(obj)
    assert result == {"a": {"key": "v2"}, "b": [1, "two"]}


def test_serialize_tool_message_dict_adds_subagent_status():
    from deerflow.runtime.serialization import serialize_lc_object

    result = serialize_lc_object(
        {
            "type": "tool",
            "content": "Task Succeeded. Result: done",
            "tool_call_id": "task-1",
        }
    )

    assert result["additional_kwargs"]["subagent_status"] == {
        "status": "completed",
        "result": "done",
    }


def test_serialize_list():
    from deerflow.runtime.serialization import serialize_lc_object

    result = serialize_lc_object([_FakePydanticV1(), 1])
    assert result == [{"key": "v1"}, 1]


def test_serialize_tuple():
    from deerflow.runtime.serialization import serialize_lc_object

    result = serialize_lc_object((_FakePydanticV2(),))
    assert result == [{"key": "v2"}]


def test_serialize_pydantic_v2():
    from deerflow.runtime.serialization import serialize_lc_object

    assert serialize_lc_object(_FakePydanticV2()) == {"key": "v2"}


def test_serialize_pydantic_v1():
    from deerflow.runtime.serialization import serialize_lc_object

    assert serialize_lc_object(_FakePydanticV1()) == {"key": "v1"}


def test_serialize_fallback_str():
    from deerflow.runtime.serialization import serialize_lc_object

    result = serialize_lc_object(object())
    assert isinstance(result, str)


def test_serialize_fallback_repr():
    from deerflow.runtime.serialization import serialize_lc_object

    assert serialize_lc_object(_Unprintable()) == "<Unprintable>"


def test_serialize_channel_values_strips_pregel_keys():
    from deerflow.runtime.serialization import serialize_channel_values

    raw = {
        "messages": ["hello"],
        "__pregel_tasks": "internal",
        "__pregel_resuming": True,
        "__interrupt__": "stop",
        "title": "Test",
    }
    result = serialize_channel_values(raw)
    assert "messages" in result
    assert "title" in result
    assert "__pregel_tasks" not in result
    assert "__pregel_resuming" not in result
    assert "__interrupt__" not in result


def test_serialize_channel_values_serializes_objects():
    from deerflow.runtime.serialization import serialize_channel_values

    result = serialize_channel_values({"obj": _FakePydanticV2()})
    assert result == {"obj": {"key": "v2"}}


def test_strip_data_url_image_blocks_removes_hidden_data_images():
    from deerflow.runtime.serialization import strip_data_url_image_blocks

    result = strip_data_url_image_blocks(
        [
            {
                "content": [
                    {"type": "text", "text": "keep"},
                    {"type": "image_url", "image_url": {"url": "data:image/png;base64,abc"}},
                ],
                "additional_kwargs": {"hide_from_ui": True},
            }
        ]
    )

    assert result == [
        {
            "content": [{"type": "text", "text": "keep"}],
            "additional_kwargs": {"hide_from_ui": True},
        }
    ]


def test_strip_data_url_image_blocks_keeps_visible_data_images():
    from deerflow.runtime.serialization import strip_data_url_image_blocks

    messages = [
        {
            "content": [{"type": "image_url", "image_url": {"url": "data:image/png;base64,abc"}}],
            "additional_kwargs": {},
        }
    ]

    assert strip_data_url_image_blocks(messages) == messages


def test_strip_data_url_image_blocks_keeps_hidden_remote_images():
    from deerflow.runtime.serialization import strip_data_url_image_blocks

    messages = [
        {
            "content": [{"type": "image_url", "image_url": {"url": "https://example.com/image.png"}}],
            "additional_kwargs": {"hide_from_ui": True},
        }
    ]

    assert strip_data_url_image_blocks(messages) == messages


def test_serialize_channel_values_for_api_strips_internal_keys_and_hidden_data_images():
    from deerflow.runtime.serialization import serialize_channel_values_for_api

    raw = {
        "messages": [
            {
                "content": [{"type": "image_url", "image_url": {"url": "data:image/png;base64,abc"}}],
                "additional_kwargs": {"hide_from_ui": True},
            },
            "plain string message",
        ],
        "__pregel_tasks": "internal",
        "__interrupt__": "stop",
    }

    assert serialize_channel_values_for_api(raw) == {
        "messages": [
            {"content": [], "additional_kwargs": {"hide_from_ui": True}},
            "plain string message",
        ]
    }


def test_serialize_messages_tuple():
    from deerflow.runtime.serialization import serialize_messages_tuple

    chunk = _FakePydanticV2()
    metadata = {"langgraph_node": "agent"}
    result = serialize_messages_tuple((chunk, metadata))
    assert result == [{"key": "v2"}, {"langgraph_node": "agent"}]


def test_serialize_messages_tuple_non_dict_metadata():
    from deerflow.runtime.serialization import serialize_messages_tuple

    result = serialize_messages_tuple((_FakePydanticV2(), "not-a-dict"))
    assert result == [{"key": "v2"}, {}]


def test_serialize_messages_tuple_fallback():
    from deerflow.runtime.serialization import serialize_messages_tuple

    result = serialize_messages_tuple("not-a-tuple")
    assert result == "not-a-tuple"


def test_serialize_dispatcher_messages_mode():
    from deerflow.runtime.serialization import serialize

    chunk = _FakePydanticV2()
    result = serialize((chunk, {"node": "x"}), mode="messages")
    assert result == [{"key": "v2"}, {"node": "x"}]


def test_serialize_dispatcher_values_mode():
    from deerflow.runtime.serialization import serialize

    result = serialize({"msg": "hi", "__pregel_tasks": "x"}, mode="values")
    assert result == {"msg": "hi"}


def test_serialize_dispatcher_default_mode():
    from deerflow.runtime.serialization import serialize

    result = serialize(_FakePydanticV1())
    assert result == {"key": "v1"}
