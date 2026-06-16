"""Import regression tests for runtime startup paths."""

import os
import subprocess
import sys
from pathlib import Path


def test_runtime_serialization_imports_without_subagent_cycle():
    backend_dir = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(backend_dir)

    result = subprocess.run(
        [sys.executable, "-c", "import deerflow.runtime.serialization"],
        cwd=backend_dir,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )

    assert result.returncode == 0, result.stderr
