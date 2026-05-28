"""Tests for nuttx_periphery.pwm with a stateful mock driver."""

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
from nuttx_periphery.pwm import PWM, PWMChannel, PWMInfoStruct, _PWMInfoStruct


class MockPWMDriver:
    """In-memory NuttX PWM driver backing store for ioctl tests."""

    def __init__(
        self,
        *,
        channel_count: int = 1,
        has_deadtime: bool = False,
        has_pulsecount: bool = False,
    ) -> None:
        self.info_type = _PWMInfoStruct(channel_count, has_deadtime, has_pulsecount)
        self.info = self.info_type()
        self.info.frequency = 20_000
        self.calls: list[tuple[int, object]] = []

    def seed_channel(self, index: int, **fields: int) -> None:
        ch = self.info.channels[index]
        for name, value in fields.items():
            setattr(ch, name, value)

    def ioctl(self, _fd: int, cmd: int, arg=0) -> int:
        self.calls.append((cmd, arg))

        if cmd == PWMIOC_GETCHARACTERISTICS:
            payload = bytes(self.info)
            for i, byte in enumerate(payload):
                arg[i] = byte
            return 0

        if cmd == PWMIOC_SETCHARACTERISTICS:
            self.info = self.info_type.from_buffer_copy(bytes(arg))
            return 0

        return 0


@pytest.fixture()
def mock_pwm(monkeypatch):
    state: dict[str, object] = {"driver": MockPWMDriver(), "fd": 77}

    def register(driver: MockPWMDriver) -> None:
        state["driver"] = driver

    def fake_open(path, flags):
        state["path"] = path
        return state["fd"]

    def fake_close(_fd):
        return None

    def fake_ioctl(fd, cmd, arg=0):
        driver = state["driver"]
        assert isinstance(driver, MockPWMDriver)
        return driver.ioctl(fd, cmd, arg)

    monkeypatch.setattr("os.open", fake_open)
    monkeypatch.setattr("os.close", fake_close)
    monkeypatch.setattr("fcntl.ioctl", fake_ioctl)
    state["register"] = register
    return state


def _drv(mock_pwm: dict) -> MockPWMDriver:
    return mock_pwm["driver"]  # type: ignore[return-value]


def test_pwm_init_reads_driver_state(mock_pwm):
    drv = MockPWMDriver()
    drv.info.frequency = 5_000
    drv.seed_channel(0, duty=32_767, cpol=1, dcpol=2, channel=3)
    mock_pwm["register"](drv)

    pwm = PWM("/dev/pwm0")
    assert pwm.frequency == 5_000
    assert pwm.channel[0].duty == 50.0
    assert pwm.channel[0].cpol == 1
    assert pwm.channel[0].dcpol == 2
    assert pwm.channel[0].channel == 3


def test_pwm_init_ioctl_sequence(mock_pwm):
    pwm = PWM("/dev/pwm0")
    drv = _drv(mock_pwm)
    get_calls = [c for c, _ in drv.calls if c == PWMIOC_GETCHARACTERISTICS]
    assert len(get_calls) >= 1
    assert pwm.pwm_info_size == ctypes.sizeof(drv.info_type)


def test_pwm_frequency_setter_updates_local_state(mock_pwm):
    pwm = PWM("/dev/pwm0")
    pwm.frequency = 1_000
    assert pwm.frequency == 1_000


def test_pwm_frequency_setter_validation(mock_pwm):
    pwm = PWM("/dev/pwm0")
    with pytest.raises(TypeError):
        pwm.frequency = "bad"
    with pytest.raises(ValueError):
        pwm.frequency = 0


def test_pwm_apply_writes_to_driver(mock_pwm):
    pwm = PWM("/dev/pwm0")
    drv = _drv(mock_pwm)
    drv.calls.clear()

    pwm.frequency = 12_000
    pwm.channel[0].duty = 75
    pwm.apply()

    set_calls = [a for c, a in drv.calls if c == PWMIOC_SETCHARACTERISTICS]
    assert len(set_calls) == 1
    written = drv.info_type.from_buffer_copy(set_calls[0])
    assert written.frequency == 12_000
    assert written.channels[0].duty == int(75 * PWMChannel.MAX_DUTY / 100)


def test_pwm_apply_roundtrip(mock_pwm):
    mock_pwm["register"](MockPWMDriver(channel_count=2, has_deadtime=True))
    pwm = PWM("/dev/pwm0", channel_count=2, has_deadtime=True)
    drv = _drv(mock_pwm)
    drv.calls.clear()

    pwm.frequency = 8_000
    pwm.channel[0].duty = 25
    pwm.channel[1].duty = 75
    pwm.channel[0].dead_time_a = 5
    pwm.channel[0].dead_time_b = 6
    pwm.apply()

    assert drv.info.frequency == 8_000
    assert pwm.channel[0].duty == 25.0
    assert pwm.channel[1].duty == 75.0
    assert pwm.channel[0].dead_time_a == 5


def test_pwm_refresh_rereads_driver(mock_pwm):
    pwm = PWM("/dev/pwm0")
    drv = _drv(mock_pwm)
    drv.info.frequency = 3_000
    drv.seed_channel(0, duty=16_383)

    pwm.refresh()
    assert pwm.frequency == 3_000
    assert pwm.channel[0].duty == 25.0


def test_pwm_multichannel(mock_pwm):
    drv = MockPWMDriver(channel_count=2, has_deadtime=True)
    drv.seed_channel(0, duty=1000, channel=1)
    drv.seed_channel(1, duty=2000, channel=2, dead_time_a=11, dead_time_b=12)
    mock_pwm["register"](drv)

    pwm = PWM("/dev/pwm0", channel_count=2, has_deadtime=True)
    assert len(pwm.channel) == 2
    assert pwm.channel[0].channel == 1
    assert pwm.channel[1].dead_time_a == 11


def test_pwm_duty_validation(mock_pwm):
    pwm = PWM("/dev/pwm0")
    with pytest.raises(TypeError):
        pwm.channel[0].duty = "x"
    with pytest.raises(ValueError):
        pwm.channel[0].duty = -1
    with pytest.raises(ValueError):
        pwm.channel[0].duty = 101


def test_pwm_start_stop(mock_pwm):
    pwm = PWM("/dev/pwm0")
    drv = _drv(mock_pwm)
    pwm.start()
    pwm.stop()
    assert PWMIOC_START in [c for c, _ in drv.calls]
    assert PWMIOC_STOP in [c for c, _ in drv.calls]


def test_pwm_fetch_and_clear_faults(mock_pwm):
    pwm = PWM("/dev/pwm0")
    drv = _drv(mock_pwm)
    pwm.fetch_and_clear_faults()
    assert PWMIOC_FAULTS_FETCH_AND_CLEAR in [c for c, _ in drv.calls]


def test_pwm_list_channels(mock_pwm):
    pwm = PWM("/dev/pwm0", channel_count=2)
    assert pwm.list_channels() == "Channels available: 2"


def test_pwm_validation(mock_pwm):
    with pytest.raises(ValueError):
        PWM("/dev/pwm0", channel_count=0)
    with pytest.raises(TypeError):
        PWM("/dev/pwm0", has_deadtime="yes")


def test_pwm_info_struct_factory():
    info = PWMInfoStruct(2, has_deadtime=True)
    assert len(info.channels) == 2
