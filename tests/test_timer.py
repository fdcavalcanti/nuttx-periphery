"""Tests for Timer API."""

from __future__ import annotations

import struct

import pytest

from nuttx_periphery.ioctl_consts import (
    TCFLAGS_ACTIVE,
    TCFLAGS_HANDLER,
    TCIOC_GETSTATUS,
    TCIOC_MAXTIMEOUT,
    TCIOC_SETTIMEOUT,
    TCIOC_START,
    TCIOC_STOP,
    TCIOC_TICK_GETSTATUS,
    TCIOC_TICK_MAXTIMEOUT,
    TCIOC_TICK_SETTIMEOUT,
)
from nuttx_periphery.timer import Timer, TimerStatus


@pytest.fixture()
def fake_timer_dev(monkeypatch):
    state = {
        "calls": [],
        "status": (TCFLAGS_ACTIVE | TCFLAGS_HANDLER, 1_000_000, 250_000),
        "tick_status": (TCFLAGS_ACTIVE, 1000, 250),
        "max_us": 0xFFFFFFFF,
        "max_ticks": 0x7FFFFFFF,
    }

    def fake_open(path, flags):
        state["open_path"] = path
        state["open_flags"] = flags
        return 55

    def fake_close(fd):
        state["closed_fd"] = fd

    def fake_ioctl(fd, cmd, arg=0):
        state["calls"].append((fd, cmd, arg))

        if cmd == TCIOC_GETSTATUS:
            struct.pack_into("@III", arg, 0, *state["status"])
            return 0

        if cmd == TCIOC_TICK_GETSTATUS:
            struct.pack_into("@III", arg, 0, *state["tick_status"])
            return 0

        if cmd == TCIOC_MAXTIMEOUT:
            arg[0] = state["max_us"]
            return 0

        if cmd == TCIOC_TICK_MAXTIMEOUT:
            arg[0] = state["max_ticks"]
            return 0

        return 0

    monkeypatch.setattr("os.open", fake_open)
    monkeypatch.setattr("os.close", fake_close)
    monkeypatch.setattr("fcntl.ioctl", fake_ioctl)
    return state


def test_timer_start_stop(fake_timer_dev):
    tmr = Timer("/dev/timer0")
    tmr.start()
    tmr.stop()

    assert (55, TCIOC_START, 0) in fake_timer_dev["calls"]
    assert (55, TCIOC_STOP, 0) in fake_timer_dev["calls"]


def test_timer_set_timeout_us(fake_timer_dev):
    tmr = Timer("/dev/timer0")
    tmr.set_timeout_us(500_000)

    assert (55, TCIOC_SETTIMEOUT, 500_000) in fake_timer_dev["calls"]


def test_timer_set_timeout_ticks(fake_timer_dev):
    tmr = Timer("/dev/timer0")
    tmr.set_timeout_ticks(123)

    assert (55, TCIOC_TICK_SETTIMEOUT, 123) in fake_timer_dev["calls"]


def test_timer_read_status_us(fake_timer_dev):
    tmr = Timer("/dev/timer0")
    status = tmr.read_status(TCIOC_GETSTATUS)

    assert isinstance(status, TimerStatus)
    assert status.flags == TCFLAGS_ACTIVE | TCFLAGS_HANDLER
    assert status.timeout == 1_000_000
    assert status.timeleft == 250_000
    assert status.active is True
    assert status.has_handler is True
    assert (55, TCIOC_GETSTATUS) in {(c[0], c[1]) for c in fake_timer_dev["calls"]}


def test_timer_read_status_ticks(fake_timer_dev):
    tmr = Timer("/dev/timer0")
    status = tmr.read_status(TCIOC_TICK_GETSTATUS)

    assert status.flags == TCFLAGS_ACTIVE
    assert status.timeout == 1000
    assert status.timeleft == 250
    assert (55, TCIOC_TICK_GETSTATUS) in {(c[0], c[1]) for c in fake_timer_dev["calls"]}


def test_timer_get_status_us(fake_timer_dev):
    tmr = Timer("/dev/timer0")
    status = tmr.get_status_us()

    assert isinstance(status, TimerStatus)
    assert status.flags == TCFLAGS_ACTIVE | TCFLAGS_HANDLER
    assert status.timeout == 1_000_000
    assert status.timeleft == 250_000
    assert status.active is True
    assert status.has_handler is True


def test_timer_get_status_ticks(fake_timer_dev):
    tmr = Timer("/dev/timer0")
    status = tmr.get_status_ticks()

    assert status.flags == TCFLAGS_ACTIVE
    assert status.timeout == 1000
    assert status.timeleft == 250
    assert status.active is True
    assert status.has_handler is False


def test_timer_max_timeout(fake_timer_dev):
    tmr = Timer("/dev/timer0")

    assert tmr.max_timeout_us() == 0xFFFFFFFF
    assert tmr.max_timeout_ticks() == 0x7FFFFFFF


def test_timer_is_active(fake_timer_dev):
    tmr = Timer("/dev/timer0")
    assert tmr.is_active() is True

    fake_timer_dev["status"] = (0, 0, 0)
    assert tmr.is_active() is False


def test_timer_status_pack_unpack():
    status = TimerStatus(flags=TCFLAGS_ACTIVE, timeout=1000, timeleft=42)
    payload = status.to_bytes()
    unpacked = TimerStatus.from_bytes(payload)

    assert unpacked == status
    assert unpacked.active is True
    assert unpacked.has_handler is False


def test_timer_status_from_bytes_validation():
    with pytest.raises(TypeError):
        TimerStatus.from_bytes(123)
    with pytest.raises(ValueError):
        TimerStatus.from_bytes(b"\x00" * 4)


def test_timer_validation(fake_timer_dev):
    tmr = Timer("/dev/timer0")

    with pytest.raises(TypeError):
        tmr.set_timeout_us("1000")
    with pytest.raises(ValueError):
        tmr.set_timeout_us(-1)
    with pytest.raises(ValueError):
        tmr.set_timeout_us(0x1_0000_0000)
    with pytest.raises(TypeError):
        tmr.set_timeout_ticks("10")
    with pytest.raises(ValueError):
        tmr.set_timeout_ticks(-1)
