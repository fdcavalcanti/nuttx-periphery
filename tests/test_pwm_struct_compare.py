"""Pytest wrapper for C/Python PWM struct binary comparison."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.skipif(shutil.which("gcc") is None, reason="gcc is required")
def test_pwm_struct_binary_compatibility() -> None:
    root = Path(__file__).resolve().parents[1]
    script = root / "tests" / "extra" /"pwm_struct_compare.py"

    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(root),
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise AssertionError(
            "PWM struct compare failed:\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
