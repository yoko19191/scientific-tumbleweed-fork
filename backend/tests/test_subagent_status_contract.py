from deerflow.subagents.status_contract import (
    parse_subagent_status_from_text,
    stamp_subagent_status,
)


def test_parse_subagent_status_success() -> None:
    assert parse_subagent_status_from_text("Task Succeeded. Result: done") == {
        "status": "completed",
        "result": "done",
    }


def test_parse_subagent_status_failure_timeout_and_cancel() -> None:
    assert parse_subagent_status_from_text("Task failed. Error: boom") == {
        "status": "failed",
        "error": "Error: boom",
    }
    assert parse_subagent_status_from_text("Task timed out. Error: slow") == {
        "status": "timed_out",
        "error": "Task timed out. Error: slow",
    }
    assert parse_subagent_status_from_text("Task cancelled by user.") == {
        "status": "cancelled",
        "error": "Task cancelled by user.",
    }


def test_stamp_subagent_status_preserves_existing_payload() -> None:
    message = {
        "type": "tool",
        "content": "Task Succeeded. Result: ignored",
        "additional_kwargs": {"subagent_status": {"status": "completed", "result": "kept"}},
    }

    assert stamp_subagent_status(message) is message
