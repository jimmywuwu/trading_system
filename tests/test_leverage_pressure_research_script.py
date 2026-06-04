from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_research_leverage_pressure_script_can_run_directly_from_repo_root() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/research_leverage_pressure_signal.py", "--help"],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Replay and summarize the leverage-pressure SHORT signal" in result.stdout
