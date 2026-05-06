"""Tests for AioSandbox concurrent command serialization (#1433)."""

import threading
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from deerflow.sandbox.exceptions import SandboxRuntimeError


@pytest.fixture()
def sandbox():
    """Create an AioSandbox with a mocked client."""
    with patch("deerflow.community.aio_sandbox.aio_sandbox.AioSandboxClient"):
        from deerflow.community.aio_sandbox.aio_sandbox import AioSandbox

        sb = AioSandbox(id="test-sandbox", base_url="http://localhost:8080")
        return sb


class TestExecuteCommandSerialization:
    """Verify that concurrent exec_command calls are serialized."""

    def test_lock_prevents_concurrent_execution(self, sandbox):
        """Concurrent threads should not overlap inside execute_command."""
        call_log = []
        barrier = threading.Barrier(3)

        def slow_exec(command, **kwargs):
            call_log.append(("enter", command))
            import time

            time.sleep(0.05)
            call_log.append(("exit", command))
            return SimpleNamespace(data=SimpleNamespace(output=f"ok: {command}"))

        sandbox._client.shell.exec_command = slow_exec

        def worker(cmd):
            barrier.wait()  # ensure all threads contend for the lock simultaneously
            sandbox.execute_command(cmd)

        threads = []
        for i in range(3):
            t = threading.Thread(target=worker, args=(f"cmd-{i}",))
            threads.append(t)

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Verify serialization: each "enter" should be followed by its own
        # "exit" before the next "enter" (no interleaving).
        enters = [i for i, (action, _) in enumerate(call_log) if action == "enter"]
        exits = [i for i, (action, _) in enumerate(call_log) if action == "exit"]
        assert len(enters) == 3
        assert len(exits) == 3
        for e_idx, x_idx in zip(enters, exits):
            assert x_idx == e_idx + 1, f"Interleaved execution detected: {call_log}"


class TestErrorObservationRetry:
    """Verify ErrorObservation detection and fresh-session retry."""

    def test_retry_on_error_observation(self, sandbox):
        """When output contains ErrorObservation, retry with a fresh session."""
        call_count = 0

        def mock_exec(command, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return SimpleNamespace(data=SimpleNamespace(output="'ErrorObservation' object has no attribute 'exit_code'"))
            return SimpleNamespace(data=SimpleNamespace(output="success"))

        sandbox._client.shell.exec_command = mock_exec

        result = sandbox.execute_command("echo hello")
        assert result == "success"
        assert call_count == 2

    def test_retry_passes_fresh_session_id(self, sandbox):
        """The retry call should include a new session id kwarg."""
        calls = []

        def mock_exec(command, **kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                return SimpleNamespace(data=SimpleNamespace(output="'ErrorObservation' object has no attribute 'exit_code'"))
            return SimpleNamespace(data=SimpleNamespace(output="ok"))

        sandbox._client.shell.exec_command = mock_exec

        sandbox.execute_command("test")
        assert len(calls) == 2
        assert "id" not in calls[0]
        assert "id" in calls[1]
        assert len(calls[1]["id"]) == 36  # UUID format

    def test_no_retry_on_clean_output(self, sandbox):
        """Normal output should not trigger a retry."""
        call_count = 0

        def mock_exec(command, **kwargs):
            nonlocal call_count
            call_count += 1
            return SimpleNamespace(data=SimpleNamespace(output="all good"))

        sandbox._client.shell.exec_command = mock_exec

        result = sandbox.execute_command("echo hello")
        assert result == "all good"
        assert call_count == 1


class TestListDirSerialization:
    """Verify that list_dir uses the file API rather than shell execution."""

    def test_list_dir_uses_file_api_and_includes_hidden_files(self, sandbox):
        """list_dir should not depend on bash and should include .gitkeep."""
        sandbox._client.shell.exec_command = MagicMock(side_effect=AssertionError("shell should not be used"))
        list_path_calls = []

        def list_path(**kwargs):
            list_path_calls.append(kwargs)
            return SimpleNamespace(
                data=SimpleNamespace(
                    files=[
                        SimpleNamespace(path="/test", is_directory=True),
                        SimpleNamespace(path="/test/.gitkeep", is_directory=False),
                        SimpleNamespace(path="/test/src", is_directory=True),
                        SimpleNamespace(path="/test/src/app.py", is_directory=False),
                        SimpleNamespace(path="/test/node_modules/skip.js", is_directory=False),
                        SimpleNamespace(path="/test-other/outside.py", is_directory=False),
                    ]
                )
            )

        sandbox._client.file.list_path = list_path
        result = sandbox.list_dir("/test")
        assert result == ["/test/.gitkeep", "/test/src/", "/test/src/app.py"]
        assert list_path_calls == [
            {
                "path": "/test",
                "recursive": True,
                "show_hidden": True,
                "max_depth": 2,
            }
        ]

    def test_list_dir_raises_instead_of_returning_fake_empty_on_api_error(self, sandbox):
        def list_path(**kwargs):
            raise RuntimeError("file API unavailable")

        sandbox._client.file.list_path = list_path

        with pytest.raises(SandboxRuntimeError, match="file API unavailable"):
            sandbox.list_dir("/test")


class TestExecCommandTimeoutCompatibility:
    """Verify shell timeout kwargs match the installed agent-sandbox SDK."""

    def test_execute_command_uses_timeout_for_current_sdk_signature(self, sandbox):
        calls = []

        def mock_exec(*, command, id=None, timeout=None):
            calls.append({"command": command, "id": id, "timeout": timeout})
            return SimpleNamespace(data=SimpleNamespace(output="ok"))

        sandbox._client.shell.exec_command = mock_exec

        sandbox.execute_command("echo hello")

        assert calls == [{"command": "echo hello", "id": None, "timeout": sandbox._DEFAULT_EXEC_TIMEOUT}]

    def test_execute_command_does_not_pass_unsupported_no_change_timeout(self, sandbox):
        def current_sdk_exec(*, command, id=None, timeout=None):
            return SimpleNamespace(data=SimpleNamespace(output=f"{command}:{timeout}:{id}"))

        sandbox._client.shell.exec_command = current_sdk_exec

        result = sandbox.execute_command("echo hello")

        assert "unexpected keyword argument 'no_change_timeout'" not in result
        assert result == f"echo hello:{sandbox._DEFAULT_EXEC_TIMEOUT}:None"

    def test_retry_uses_same_timeout_kwarg(self, sandbox):
        calls = []

        def mock_exec(*, command, id=None, timeout=None):
            calls.append({"id": id, "timeout": timeout})
            if len(calls) == 1:
                return SimpleNamespace(data=SimpleNamespace(output="'ErrorObservation' object has no attribute 'exit_code'"))
            return SimpleNamespace(data=SimpleNamespace(output="ok"))

        sandbox._client.shell.exec_command = mock_exec

        sandbox.execute_command("echo hello")

        assert len(calls) == 2
        assert calls[0] == {"id": None, "timeout": sandbox._DEFAULT_EXEC_TIMEOUT}
        assert calls[1]["id"] is not None
        assert calls[1]["timeout"] == sandbox._DEFAULT_EXEC_TIMEOUT

    def test_future_no_change_timeout_signature_is_supported(self, sandbox):
        calls = []

        def mock_exec(*, command, id=None, no_change_timeout=None):
            calls.append({"command": command, "id": id, "no_change_timeout": no_change_timeout})
            return SimpleNamespace(data=SimpleNamespace(output="ok"))

        sandbox._client.shell.exec_command = mock_exec

        sandbox.execute_command("echo hello")

        assert calls == [{"command": "echo hello", "id": None, "no_change_timeout": sandbox._DEFAULT_EXEC_TIMEOUT}]


class TestReadFile:
    """Verify text reads are stable and binary reads fail clearly."""

    def test_read_file_downloads_and_decodes_text(self, sandbox):
        sandbox._client.file.download_file = lambda **kwargs: iter([b"hello ", b"world\n"])

        assert sandbox.read_file("/test/readme.txt") == "hello world\n"

    def test_read_file_rejects_elf_binary(self, sandbox):
        sandbox._client.file.download_file = lambda **kwargs: iter([b"\x7fELF\x02\x01\x01\0binary"])

        result = sandbox.read_file("/test/tool")

        assert result == "Error: Cannot read binary file with read_file: /test/tool"

    def test_read_file_stops_downloading_binary_after_detection(self, sandbox):
        consumed = []

        def chunks():
            yield b"\x7fELF\x02\x01\x01\0binary"
            consumed.append("second")
            yield b"large trailing payload"

        sandbox._client.file.download_file = lambda **kwargs: chunks()

        result = sandbox.read_file("/test/tool")

        assert result == "Error: Cannot read binary file with read_file: /test/tool"
        assert consumed == []

    def test_read_file_truncates_large_stream_without_consuming_tail(self, sandbox):
        sandbox._MAX_READ_FILE_BYTES = 5
        consumed = []

        def chunks():
            yield b"hello"
            yield b"world"
            consumed.append("tail")
            yield b"tail"

        sandbox._client.file.download_file = lambda **kwargs: chunks()

        result = sandbox.read_file("/test/large.txt")

        assert result.startswith("hello")
        assert "truncated" in result
        assert consumed == []


class TestConcurrentFileWrites:
    """Verify file write paths do not lose concurrent updates."""

    def test_append_should_preserve_both_parallel_writes(self, sandbox):
        storage = {"content": "seed\n"}
        writes = []
        state_lock = threading.Lock()

        def write_back(*, file, content, append=False, **kwargs):
            with state_lock:
                writes.append({"file": file, "content": content, "append": append})
                if append:
                    storage["content"] += content
                else:
                    storage["content"] = content
            return SimpleNamespace(data=SimpleNamespace())

        sandbox.read_file = MagicMock(side_effect=AssertionError("append should not read existing content"))
        sandbox._client.file.write_file = write_back

        barrier = threading.Barrier(2)

        def writer(payload: str):
            barrier.wait()
            sandbox.write_file("/tmp/shared.log", payload, append=True)

        threads = [
            threading.Thread(target=writer, args=("A\n",)),
            threading.Thread(target=writer, args=("B\n",)),
        ]

        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert storage["content"] in {"seed\nA\nB\n", "seed\nB\nA\n"}
        assert [write["append"] for write in writes] == [True, True]
