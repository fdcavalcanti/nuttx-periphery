"""Pytest configuration for local src/ layout imports."""

from __future__ import annotations

import os
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

# Propagate src/ to PYTHONPATH so spawned subprocesses can import the package.
# In-process imports are handled via [tool.pytest.ini_options] pythonpath.
_existing = os.environ.get("PYTHONPATH", "")
_parts = _existing.split(os.pathsep) if _existing else []
if str(SRC) not in _parts:
    os.environ["PYTHONPATH"] = (
        f"{SRC}{os.pathsep}{_existing}" if _existing else str(SRC)
    )


@pytest.fixture()
def record_xml_attribute():
    """No-op replacement to avoid PytestExperimentalApiWarning spam."""

    def _record_xml_attribute(name: str, value: object) -> None:
        _ = (name, value)

    return _record_xml_attribute
