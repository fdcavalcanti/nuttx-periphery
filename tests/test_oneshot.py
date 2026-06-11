"""Tests for Oneshot timer API and example script."""

from __future__ import annotations

import importlib.util
import signal
import sys
from pathlib import Path

import pytest

from nuttx_periphery.ioctl_consts import (
    OSIOC_CANCEL,
    OSIOC_CURRENT,
    OSIOC_MAXDELAY,
    OSIOC_START,
    SIGEV_SIGNAL,
)
from nuttx_periphery.oneshot import OneshotStartStruct, OneshotTimer, Timespec
from nuttx_periphery.sigevent import Sigevent

EXAMPLE_PATH = Path(__file__).resolve().parents[1] / "examples" / "oneshot.py"


def _load_oneshot_example():
    spec = importlib.util.spec_from_file_location("oneshot_example", EXAMPLE_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["oneshot_example"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def fake_oneshot_dev(monkeypatch):
    state = {
        "calls": [],
        "max_delay": (3600, 500_000_000),
        "current": (42, 123_456_789),
        "cancel_remaining": (1, 500_000_000),
        "start": None,
    }

    def fake_open(path, flags):
        state["open_path"] = path
        state["open_flags"] = flags
        return 77

    def fake_close(fd):
        state["closed_fd"] = fd

    def fake_ioctl(fd, cmd, arg=0):
        state["calls"].append((fd, cmd, arg))

        if cmd == OSIOC_MAXDELAY:
            arg.tv_sec, arg.tv_nsec = state["max_delay"]
            return 0

        if cmd == OSIOC_CURRENT:
            arg.tv_sec, arg.tv_nsec = state["current"]
            return 0

        if cmd == OSIOC_CANCEL:
            arg.tv_sec, arg.tv_nsec = state["cancel_remaining"]
            return 0

        if cmd == OSIOC_START:
            state["start"] = OneshotStartStruct.from_buffer_copy(bytes(arg))
            return 0

        return 0

    monkeypatch.setattr("os.open", fake_open)
    monkeypatch.setattr("os.close", fake_close)
    monkeypatch.setattr("fcntl.ioctl", fake_ioctl)
    return state


def test_timespec_from_timeout_us():
    ts = Timespec.from_timeout_us(2_500_000)
    assert ts.tv_sec == 2
    assert ts.tv_nsec == 500_000_000

    ts = Timespec.from_timeout_us(1_000_000)
    assert ts.tv_sec == 1
    assert ts.tv_nsec == 0

    ts = Timespec.from_timeout_us(500)
    assert ts.tv_sec == 0
    assert ts.tv_nsec == 500_000


def test_timespec_struct_roundtrip():
    original = Timespec(tv_sec=10, tv_nsec=250_000)
    restored = Timespec.from_struct(original.to_struct())
    assert restored == original


def test_timespec_from_timeout_us_validation():
    with pytest.raises(TypeError):
        Timespec.from_timeout_us("1000")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        Timespec.from_timeout_us(-1)
    with pytest.raises(ValueError):
        Timespec.from_timeout_us(0x1_0000_0000)


def test_oneshot_max_delay(fake_oneshot_dev):
    oneshot = OneshotTimer("/dev/oneshot")
    delay = oneshot.max_delay()

    assert isinstance(delay, Timespec)
    assert delay.tv_sec == 3600
    assert delay.tv_nsec == 500_000_000
    assert (77, OSIOC_MAXDELAY) in {(c[0], c[1]) for c in fake_oneshot_dev["calls"]}


def test_oneshot_current(fake_oneshot_dev):
    oneshot = OneshotTimer("/dev/oneshot")
    current = oneshot.current()

    assert current.tv_sec == 42
    assert current.tv_nsec == 123_456_789
    assert (77, OSIOC_CURRENT) in {(c[0], c[1]) for c in fake_oneshot_dev["calls"]}


def test_oneshot_cancel(fake_oneshot_dev):
    oneshot = OneshotTimer("/dev/oneshot")
    remaining = oneshot.cancel()

    assert remaining.tv_sec == 1
    assert remaining.tv_nsec == 500_000_000
    assert (77, OSIOC_CANCEL) in {(c[0], c[1]) for c in fake_oneshot_dev["calls"]}


def test_oneshot_set_timeout_us(fake_oneshot_dev):
    oneshot = OneshotTimer("/dev/oneshot")
    oneshot.set_timeout_us(500_000)

    assert oneshot._timeout_us == 500_000
    assert not any(cmd == OSIOC_START for _, cmd, _ in fake_oneshot_dev["calls"])


def test_oneshot_start_uses_configured_values(fake_oneshot_dev, monkeypatch):
    monkeypatch.setattr("os.getpid", lambda: 99)

    oneshot = OneshotTimer("/dev/oneshot")
    oneshot.set_timeout_us(2_000_000)
    oneshot.set_signo(10)
    oneshot.start()

    assert (77, OSIOC_START) in {(c[0], c[1]) for c in fake_oneshot_dev["calls"]}
    start = fake_oneshot_dev["start"]
    assert start is not None
    assert start.pid == 99
    assert start.ts.tv_sec == 2
    assert start.ts.tv_nsec == 0
    assert start.event.sigev_notify == SIGEV_SIGNAL
    assert start.event.sigev_signo == 10
    assert start.event._tid == 99


def test_oneshot_start_with_overrides(fake_oneshot_dev):
    oneshot = OneshotTimer("/dev/oneshot")
    oneshot.set_timeout_us(1_000_000)
    oneshot.set_signo(signal.SIGUSR1)
    oneshot.start(signo=32, pid=7, timeout_us=3_500_000)

    start = fake_oneshot_dev["start"]
    assert start is not None
    assert start.pid == 7
    assert start.ts.tv_sec == 3
    assert start.ts.tv_nsec == 500_000_000
    assert start.event.sigev_signo == 32
    assert start.event._tid == 7


def test_oneshot_start_default_signo(fake_oneshot_dev, monkeypatch):
    monkeypatch.setattr("os.getpid", lambda: 1)

    oneshot = OneshotTimer("/dev/oneshot")
    oneshot.start(timeout_us=1_000_000)

    start = fake_oneshot_dev["start"]
    assert start is not None
    assert start.event.sigev_signo == signal.SIGUSR1


def test_oneshot_start_matches_sigevent_bytes(fake_oneshot_dev, monkeypatch):
    monkeypatch.setattr("os.getpid", lambda: 55)

    oneshot = OneshotTimer("/dev/oneshot")
    oneshot.start(signo=15, pid=55, timeout_us=1_000_000)

    start = fake_oneshot_dev["start"]
    expected_event = Sigevent.signal(15, thread_id=55).to_bytes()
    assert bytes(start.event) == expected_event


def test_oneshot_validation(fake_oneshot_dev):
    oneshot = OneshotTimer("/dev/oneshot")

    with pytest.raises(TypeError):
        oneshot.set_timeout_us("1000")
    with pytest.raises(ValueError):
        oneshot.set_timeout_us(-1)
    with pytest.raises(ValueError):
        oneshot.set_timeout_us(0x1_0000_0000)

    with pytest.raises(TypeError):
        oneshot.set_signo("10")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        oneshot.set_signo(0)
    with pytest.raises(ValueError):
        oneshot.set_signo(64)

    with pytest.raises(TypeError):
        oneshot.start(pid="1")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        oneshot.start(pid=0)
    with pytest.raises(ValueError):
        oneshot.start(signo=0)
    with pytest.raises(ValueError):
        oneshot.start(timeout_us=-1)


def test_oneshot_ioctl_error(fake_oneshot_dev, monkeypatch):
    def failing_ioctl(fd, cmd, arg=0):
        fake_oneshot_dev["calls"].append((fd, cmd, arg))
        return -1

    monkeypatch.setattr("fcntl.ioctl", failing_ioctl)

    oneshot = OneshotTimer("/dev/oneshot")

    with pytest.raises(RuntimeError, match="Error reading timespec"):
        oneshot.max_delay()
    with pytest.raises(RuntimeError, match="Error starting oneshot timer"):
        oneshot.start(timeout_us=1_000_000)


def test_oneshot_example_parse_args_defaults(monkeypatch):
    mod = _load_oneshot_example()
    monkeypatch.setattr(sys, "argv", ["oneshot.py"])

    args = mod.parse_args()
    assert args.oneshot == "/dev/oneshot"
    assert args.timeout == mod.DEFAULT_TIMEOUT_SEC


def test_oneshot_example_parse_args_custom(monkeypatch):
    mod = _load_oneshot_example()
    monkeypatch.setattr(
        sys,
        "argv",
        ["oneshot.py", "--timeout", "5.5", "/dev/oneshot1"],
    )

    args = mod.parse_args()
    assert args.oneshot == "/dev/oneshot1"
    assert args.timeout == 5.5


def test_oneshot_example_main_rejects_non_positive_timeout(capsys):
    mod = _load_oneshot_example()

    assert mod.main("/dev/oneshot", 0) == 1
    assert mod.main("/dev/oneshot", -1.0) == 1

    err = capsys.readouterr().err
    assert "--timeout must be > 0" in err
