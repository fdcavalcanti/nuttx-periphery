"""C/Python PWM struct binary compatibility tests."""

from __future__ import annotations

import ctypes
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from nuttx_periphery.pwm import PWMInfoStruct

HERE = Path(__file__).resolve().parent
PROBE_C = HERE / "extra" / "pwm_struct_probe.c"

POINTER_SIZE = ctypes.sizeof(ctypes.c_void_p)
ARG_VALUE = 0x1122334455667788 if POINTER_SIZE == 8 else 0x55667788

pytestmark = [
    pytest.mark.skipif(shutil.which("gcc") is None, reason="gcc is required"),
    pytest.mark.skipif(
        POINTER_SIZE not in (4, 8), reason="Unsupported host pointer size"
    ),
]


def _build_and_run(defines: list[str]) -> bytes:
    with tempfile.TemporaryDirectory() as tmpdir:
        bin_path = Path(tmpdir) / "pwm_probe"
        cmd = [
            "gcc",
            "-std=c11",
            "-Wall",
            "-Wextra",
            "-O0",
            str(PROBE_C),
            "-o",
            str(bin_path),
            f"-DPOINTER_SIZE={POINTER_SIZE}",
            *defines,
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        result = subprocess.run([str(bin_path)], check=True, capture_output=True)
        return result.stdout


def _expected_single(has_deadtime: bool, has_pulsecount: bool) -> bytes:
    info = PWMInfoStruct(1, has_deadtime, has_pulsecount)
    info.frequency = 20000
    info.channels[0].duty = 1000
    info.channels[0].cpol = 1
    info.channels[0].dcpol = 2
    info.channels[0].channel = 0
    if has_deadtime:
        info.channels[0].dead_time_a = 11
        info.channels[0].dead_time_b = 12
    if has_pulsecount:
        info.channels[0].count = 33
    info.arg = ARG_VALUE
    return bytes(info)


def _expected_multi(has_deadtime: bool) -> bytes:
    info = PWMInfoStruct(2, has_deadtime)
    info.frequency = 20000
    info.channels[0].duty = 1000
    info.channels[0].cpol = 1
    info.channels[0].dcpol = 2
    info.channels[0].channel = 0
    info.channels[1].duty = 2000
    info.channels[1].cpol = 0
    info.channels[1].dcpol = 1
    info.channels[1].channel = -1
    if has_deadtime:
        info.channels[0].dead_time_a = 11
        info.channels[0].dead_time_b = 12
        info.channels[1].dead_time_a = 21
        info.channels[1].dead_time_b = 22
    info.arg = ARG_VALUE
    return bytes(info)


@pytest.mark.parametrize(
    ("name", "defines", "expected"),
    [
        (
            "single",
            ["-DCHANNEL_COUNT=1"],
            lambda: _expected_single(has_deadtime=False, has_pulsecount=False),
        ),
        (
            "single+deadtime+pulsecount",
            ["-DCHANNEL_COUNT=1", "-DHAS_DEADTIME", "-DHAS_PULSECOUNT"],
            lambda: _expected_single(has_deadtime=True, has_pulsecount=True),
        ),
        (
            "multichan",
            ["-DCHANNEL_COUNT=2"],
            lambda: _expected_multi(has_deadtime=False),
        ),
        (
            "multichan+deadtime",
            ["-DCHANNEL_COUNT=2", "-DHAS_DEADTIME"],
            lambda: _expected_multi(has_deadtime=True),
        ),
    ],
    ids=lambda v: v if isinstance(v, str) else None,
)
def test_pwm_struct_binary_compatibility(
    name: str, defines: list[str], expected
) -> None:
    c_bytes = _build_and_run(defines)
    py_bytes = expected()
    assert c_bytes == py_bytes, (
        f"{name}: mismatch\n"
        f"C  ({len(c_bytes)}): {c_bytes.hex()}\n"
        f"PY ({len(py_bytes)}): {py_bytes.hex()}"
    )
