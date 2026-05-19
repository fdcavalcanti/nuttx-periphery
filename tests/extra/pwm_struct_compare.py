#!/usr/bin/env python3
"""Compare C struct binary vs Python PWMInfo serialization."""

from __future__ import annotations

import ctypes
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from nuttx_periphery.pwm import PWMChannel, PWMInfo


def build_and_run(defines: list[str]) -> bytes:
    src = ROOT / "tests" / "extra" / "pwm_struct_probe.c"
    with tempfile.TemporaryDirectory() as tmpdir:
        bin_path = Path(tmpdir) / "pwm_probe"
        cmd = ["gcc", "-std=c11", "-Wall", "-Wextra", "-O0", str(src), "-o", str(bin_path)] + defines
        subprocess.run(cmd, check=True, capture_output=True)
        result = subprocess.run([str(bin_path)], check=True, capture_output=True)
        return result.stdout


def expected_single(pointer_size: int, has_deadtime: bool, has_pulsecount: bool) -> bytes:
    arg = 0x1122334455667788 if pointer_size == 8 else 0x55667788
    info = PWMInfo(
        frequency=20000,
        duty=1000,
        cpol=1,
        dcpol=2,
        arg=arg,
        dead_time_a=11 if has_deadtime else None,
        dead_time_b=12 if has_deadtime else None,
        count=33 if has_pulsecount else None,
        channels=[
            PWMChannel(
                duty=1000,
                cpol=1,
                dcpol=2,
                channel=0,
                dead_time_a=11 if has_deadtime else None,
                dead_time_b=12 if has_deadtime else None,
                count=33 if has_pulsecount else None,
            )
        ],
    )
    return info.to_bytes(
        channel_count=1,
        has_deadtime=has_deadtime,
        has_pulsecount=has_pulsecount,
    )


def expected_multi(pointer_size: int, has_deadtime: bool) -> bytes:
    arg = 0x1122334455667788 if pointer_size == 8 else 0x55667788
    info = PWMInfo(
        frequency=20000,
        arg=arg,
        channels=[
            PWMChannel(
                duty=1000,
                cpol=1,
                dcpol=2,
                channel=0,
                dead_time_a=11 if has_deadtime else None,
                dead_time_b=12 if has_deadtime else None,
            ),
            PWMChannel(
                duty=2000,
                cpol=0,
                dcpol=1,
                channel=-1,
                dead_time_a=21 if has_deadtime else None,
                dead_time_b=22 if has_deadtime else None,
            ),
        ],
    )
    return info.to_bytes(channel_count=2, has_deadtime=has_deadtime)


def compare_case(name: str, c_bytes: bytes, py_bytes: bytes) -> None:
    if c_bytes != py_bytes:
        raise SystemExit(
            f"{name}: mismatch\n"
            f"C  ({len(c_bytes)}): {c_bytes.hex()}\n"
            f"PY ({len(py_bytes)}): {py_bytes.hex()}"
        )
    print(f"{name}: OK ({len(c_bytes)} bytes)")


def main() -> None:
    pointer_size = ctypes.sizeof(ctypes.c_void_p)
    if pointer_size not in (4, 8):
        raise SystemExit("Unsupported host pointer size")

    base_define = [f"-DPOINTER_SIZE={pointer_size}"]

    c_single = build_and_run(base_define + ["-DCHANNEL_COUNT=1"])
    compare_case(
        "single",
        c_single,
        expected_single(pointer_size, has_deadtime=False, has_pulsecount=False),
    )

    c_single_dt_pc = build_and_run(
        base_define + ["-DCHANNEL_COUNT=1", "-DHAS_DEADTIME", "-DHAS_PULSECOUNT"]
    )
    compare_case(
        "single+deadtime+pulsecount",
        c_single_dt_pc,
        expected_single(pointer_size, has_deadtime=True, has_pulsecount=True),
    )

    c_multi = build_and_run(base_define + ["-DCHANNEL_COUNT=2"])
    compare_case(
        "multichan",
        c_multi,
        expected_multi(pointer_size, has_deadtime=False),
    )

    c_multi_dt = build_and_run(base_define + ["-DCHANNEL_COUNT=2", "-DHAS_DEADTIME"])
    compare_case(
        "multichan+deadtime",
        c_multi_dt,
        expected_multi(pointer_size, has_deadtime=True),
    )

    print("All PWM struct binary comparisons passed.")


if __name__ == "__main__":
    main()
