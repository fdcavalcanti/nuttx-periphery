"""Pytest configuration for local src/ layout imports."""

from __future__ import annotations

import pathlib
import sys

import pytest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture()
def record_xml_attribute():
    """No-op replacement to avoid PytestExperimentalApiWarning spam."""

    def _record_xml_attribute(name: str, value: object) -> None:
        _ = (name, value)

    return _record_xml_attribute
