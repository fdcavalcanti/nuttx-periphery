"""Tests for PWM API."""

from __future__ import annotations

import ctypes

import pytest

from nuttx_periphery.ioctl_consts import (
    PWMIOC_FAULTS_FETCH_AND_CLEAR,
    PWMIOC_GETCHARACTERISTICS,
    PWMIOC_SETCHARACTERISTICS,
    PWMIOC_START,
    PWMIOC_STOP,
)
from nuttx_periphery.pwm import PWM, PWMChannel, PWMInfo


@pytest.fixture()
def fake_pwm_dev(monkeypatch):
    state = {"calls": []}

    def fake_open(path, flags):
        state["open_path"] = path
        state["open_flags"] = flags
        return 77

    def fake_close(fd):
        state["closed_fd"] = fd

    def fake_ioctl(fd, cmd, arg=0):
        state["calls"].append((fd, cmd, arg))

        if cmd == PWMIOC_GETCHARACTERISTICS:
            for i in range(len(arg)):
                arg[i] = i & 0xFF
            return 0

        if cmd == PWMIOC_FAULTS_FETCH_AND_CLEAR and not isinstance(arg, int):
            arg[0] = 0xA5
            return 0

        return 0

    monkeypatch.setattr("os.open", fake_open)
    monkeypatch.setattr("os.close", fake_close)
    monkeypatch.setattr("fcntl.ioctl", fake_ioctl)
    return state


def test_pwm_set_get_characteristics(fake_pwm_dev):
    pwm = PWM("/dev/pwm0")
    pwm.set_characteristics(b"\x01\x02")
    data = pwm._get_charateristics(4)
    assert data == b"\x00\x01\x02\x03"
    assert (77, PWMIOC_SETCHARACTERISTICS, b"\x01\x02") in fake_pwm_dev["calls"]


def test_pwm_get_characteristics_default_size(fake_pwm_dev):
    pwm = PWM("/dev/pwm0")
    info = pwm.get_characteristics()

    assert isinstance(info, PWMInfo)
    read_calls = [c for c in fake_pwm_dev["calls"] if c[1] == PWMIOC_GETCHARACTERISTICS]
    assert len(read_calls) == 1
    pointer = ctypes.sizeof(ctypes.c_void_p)
    expected = 4 + 4 + 2
    expected += (-expected) % pointer
    expected += pointer
    assert len(read_calls[0][2]) == expected


def test_pwm_get_characteristics_multichan_size(fake_pwm_dev):
    pwm = PWM("/dev/pwm0", channel_count=2, has_deadtime=True)
    info = pwm.get_characteristics()

    assert isinstance(info, PWMInfo)
    assert info.channels is not None
    assert len(info.channels) == 2
    read_calls = [c for c in fake_pwm_dev["calls"] if c[1] == PWMIOC_GETCHARACTERISTICS]
    assert len(read_calls) == 1
    pointer = ctypes.sizeof(ctypes.c_void_p)
    chan_size = 4 + 8 + 3
    chan_size += (-chan_size) % 4
    expected = 4 + 2 * chan_size
    expected += (-expected) % pointer
    expected += pointer
    assert len(read_calls[0][2]) == expected


def test_pwm_info_pack_unpack():
    info = PWMInfo(frequency=1000, duty=32768, cpol=1, dcpol=2, arg=0x1234, count=10)
    payload = info.to_bytes(has_pulsecount=True)
    unpacked = PWMInfo.from_bytes(payload, has_pulsecount=True)

    assert unpacked.frequency == 1000
    assert unpacked.duty == 32768
    assert unpacked.cpol == 1
    assert unpacked.dcpol == 2
    assert unpacked.arg == 0x1234
    assert unpacked.count == 10


def test_pwm_info_multichan_pack_unpack():
    info = PWMInfo(
        frequency=20_000,
        arg=0x44,
        channels=[
            PWMChannel(duty=1000, channel=1, cpol=1, dcpol=2),
            PWMChannel(duty=2000, channel=-1, cpol=0, dcpol=1),
        ],
    )
    payload = info.to_bytes(channel_count=2)
    unpacked = PWMInfo.from_bytes(payload, channel_count=2)

    assert unpacked.frequency == 20_000
    assert unpacked.arg == 0x44
    assert unpacked.channels is not None
    assert len(unpacked.channels) == 2
    assert unpacked.channels[0].channel == 1
    assert unpacked.channels[1].channel == -1


def test_pwm_set_characteristics_with_pwm_info(fake_pwm_dev):
    pwm = PWM("/dev/pwm0")
    info = PWMInfo(frequency=10, duty=1)
    pwm.set_characteristics(info)

    sent = [c for c in fake_pwm_dev["calls"] if c[1] == PWMIOC_SETCHARACTERISTICS]
    assert len(sent) == 1
    assert isinstance(sent[0][2], bytes)


def test_pwm_new_pwm_info_single_channel_defaults(fake_pwm_dev):
    pwm = PWM("/dev/pwm0", has_deadtime=True, has_pulsecount=True)
    info = pwm.new_pwm_info(frequency=1000, duty=123)

    assert isinstance(info, PWMInfo)
    assert info.frequency == 1000
    assert info.duty == 123
    assert info.dead_time_a == 0
    assert info.dead_time_b == 0
    assert info.count == 0
    assert info.channels is not None
    assert len(info.channels) == 1
    assert info.channels[0].duty == 123
    assert info.channels[0].count == 0


def test_pwm_new_pwm_info_multichan_defaults(fake_pwm_dev):
    pwm = PWM("/dev/pwm0", channel_count=2)
    info = pwm.new_pwm_info(frequency=20_000)

    assert isinstance(info, PWMInfo)
    assert info.frequency == 20_000
    assert info.channels is not None
    assert len(info.channels) == 2
    assert info.channels[0].channel == 1
    assert info.channels[1].channel == 2


def test_pwm_start_stop(fake_pwm_dev):
    pwm = PWM("/dev/pwm0")
    pwm.start()
    pwm.stop()
    assert (77, PWMIOC_START, 0) in fake_pwm_dev["calls"]
    assert (77, PWMIOC_STOP, 0) in fake_pwm_dev["calls"]


def test_pwm_faults_fetch_and_clear(fake_pwm_dev):
    pwm = PWM("/dev/pwm0")
    assert pwm.faults_fetch_and_clear() is None
    value = pwm.faults_fetch_and_clear(0x03)
    assert value == 0xA5


def test_pwm_validation(fake_pwm_dev):
    pwm = PWM("/dev/pwm0")
    with pytest.raises(TypeError):
        pwm.set_characteristics(1)
    with pytest.raises(ValueError):
        PWMInfo(frequency=1, duty=1, dead_time_a=1).to_bytes(has_deadtime=True)
    PWMInfo(frequency=1, duty=1, count=2).to_bytes()
    with pytest.raises(ValueError):
        PWM("/dev/pwm0", channel_count=0)
    pwm_channels = PWM("/dev/pwm0", channel_count=2, has_pulsecount=True)
    assert pwm_channels.has_pulsecount is True
    info = PWM("/dev/pwm0").new_pwm_info(
        frequency=10,
        channels=[PWMChannel(duty=0, channel=1)],
    )
    assert info.channels is not None
    assert len(info.channels) == 1
    with pytest.raises(TypeError):
        pwm._get_charateristics("4")
    with pytest.raises(ValueError):
        pwm._get_charateristics(0)
    with pytest.raises(TypeError):
        pwm.faults_fetch_and_clear("1")
    with pytest.raises(ValueError):
        pwm.faults_fetch_and_clear(-1)
