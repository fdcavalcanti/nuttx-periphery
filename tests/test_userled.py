"""Tests for UserLED API."""

from __future__ import annotations

import pytest

from nuttx_periphery.ioctl_consts import (
    ULEDIOC_GETALL,
    ULEDIOC_SETALL,
    ULEDIOC_SETLED,
    ULEDIOC_SUPPORTED,
)
from nuttx_periphery.userled import UserLED


@pytest.fixture()
def fake_led_dev(monkeypatch):
    state = {"calls": []}

    def fake_open(path, flags):
        state["open_path"] = path
        state["open_flags"] = flags
        return 9

    def fake_close(fd):
        state["closed_fd"] = fd

    def fake_ioctl(fd, cmd, arg=0):
        state["calls"].append((fd, cmd, arg))
        if cmd == ULEDIOC_SUPPORTED:
            arg[0] = 0b111
        if cmd == ULEDIOC_GETALL:
            arg[0] = 0b101
        return 0

    monkeypatch.setattr("os.open", fake_open)
    monkeypatch.setattr("os.close", fake_close)
    monkeypatch.setattr("fcntl.ioctl", fake_ioctl)
    return state


def test_userled_supported_and_get_all(fake_led_dev):
    led = UserLED("/dev/userleds")
    assert led.supported() == 0b111
    assert led.get_all() == 0b101


def test_userled_set_all(fake_led_dev):
    led = UserLED("/dev/userleds")
    led.set_all(0b010)

    assert (9, ULEDIOC_SETALL, 0b010) in fake_led_dev["calls"]


def test_userled_set_led(fake_led_dev):
    led = UserLED("/dev/userleds")
    led.set_led(2, True)

    matching = [c for c in fake_led_dev["calls"] if c[1] == ULEDIOC_SETLED]
    assert len(matching) == 1
    assert bytes(matching[0][2]) == b"\x02\x01"


def test_userled_validation(fake_led_dev):
    led = UserLED("/dev/userleds")

    with pytest.raises(TypeError):
        led.set_all("3")
    with pytest.raises(ValueError):
        led.set_all(-1)
    with pytest.raises(TypeError):
        led.set_led("0", True)
    with pytest.raises(ValueError):
        led.set_led(-1, True)
    with pytest.raises(TypeError):
        led.set_led(0, 1)
