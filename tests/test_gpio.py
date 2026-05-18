"""Tests for the GPIO and CharacterDevice APIs."""

from __future__ import annotations

from array import array

import pytest

from nuttx_periphery.device import CharacterDevice
from nuttx_periphery.gpio import GPIO, GPIOPinType
from nuttx_periphery.ioctl_consts import (
    GPIOC_IRQ_SETMASK,
    GPIOC_PINTYPE,
    GPIOC_READ,
    GPIOC_REGISTER,
    GPIOC_SETDEBOUNCE,
    GPIOC_SETPINTYPE,
    GPIOC_UNREGISTER,
    GPIOC_WRITE,
)


@pytest.fixture()
def fake_dev(monkeypatch):
    state = {"open_flags": None, "closed_fd": None, "calls": []}

    def fake_open(path, flags):
        state["open_path"] = path
        state["open_flags"] = flags
        return 42

    def fake_close(fd):
        state["closed_fd"] = fd

    def fake_read(fd, size):
        state["read"] = (fd, size)
        return b"\xAA\x55"[:size]

    def fake_ioctl(fd, cmd, arg=0):
        state["calls"].append((fd, cmd, arg))

        if cmd == GPIOC_READ:
            arg[0] = 1
            return 0

        if cmd == GPIOC_PINTYPE:
            arg[0] = int(GPIOPinType.GPIO_OUTPUT_PIN)
            return 0

        return 0

    monkeypatch.setattr("os.open", fake_open)
    monkeypatch.setattr("os.close", fake_close)
    monkeypatch.setattr("os.read", fake_read)
    monkeypatch.setattr("fcntl.ioctl", fake_ioctl)
    return state


def test_character_device_open_close(fake_dev):
    dev = CharacterDevice("/dev/gpio0", nonblock=True)

    assert dev.path == "/dev/gpio0"
    assert dev.fileno() == 42
    assert fake_dev["open_path"] == "/dev/gpio0"
    assert fake_dev["open_flags"] != 0

    dev.close()
    assert fake_dev["closed_fd"] == 42


def test_character_device_closed_fileno_raises(fake_dev):
    dev = CharacterDevice("/dev/gpio0")
    dev.close()

    with pytest.raises(ValueError):
        dev.fileno()


def test_character_device_read(fake_dev):
    dev = CharacterDevice("/dev/gpio0")
    buf = bytearray(4)
    nread = dev.read(buf, 2)

    assert nread == 2
    assert bytes(buf[:2]) == b"\xAA\x55"
    assert fake_dev["read"] == (42, 2)


def test_gpio_read_write(fake_dev):
    gpio = GPIO("/dev/gpio0")

    assert gpio.read() is True

    gpio.write(False)
    gpio.write(True)

    assert (42, GPIOC_WRITE, 0) in fake_dev["calls"]
    assert (42, GPIOC_WRITE, 1) in fake_dev["calls"]


def test_gpio_pin_type_get_set(fake_dev):
    gpio = GPIO("/dev/gpio0")

    assert gpio.get_pin_type() == GPIOPinType.GPIO_OUTPUT_PIN
    gpio.set_pin_type(GPIOPinType.GPIO_INTERRUPT_RISING_PIN)
    gpio.set_pin_type(3)

    assert (42, GPIOC_SETPINTYPE, int(GPIOPinType.GPIO_INTERRUPT_RISING_PIN)) in fake_dev["calls"]
    assert (42, GPIOC_SETPINTYPE, 3) in fake_dev["calls"]


def test_gpio_other_ioctls(fake_dev):
    gpio = GPIO("/dev/gpio0")

    gpio.set_debounce_ns(1000)
    gpio.set_irq_mask(True)
    gpio.register_signal(10)
    gpio.unregister_signal()

    assert (42, GPIOC_SETDEBOUNCE, 1000) in fake_dev["calls"]
    assert (42, GPIOC_IRQ_SETMASK, 1) in fake_dev["calls"]
    assert (42, GPIOC_REGISTER, 10) in fake_dev["calls"]
    assert (42, GPIOC_UNREGISTER, 0) in fake_dev["calls"]


def test_gpio_validation(fake_dev):
    gpio = GPIO("/dev/gpio0")

    with pytest.raises(TypeError):
        gpio.write(1)
    with pytest.raises(TypeError):
        gpio.set_pin_type("out")
    with pytest.raises(TypeError):
        gpio.set_debounce_ns("10")
    with pytest.raises(ValueError):
        gpio.set_debounce_ns(-1)
    with pytest.raises(TypeError):
        gpio.set_irq_mask(1)
    with pytest.raises(TypeError):
        gpio.register_signal("2")
    with pytest.raises(ValueError):
        gpio.register_signal(0)


def test_ioctl_raw_with_mutable_buffer(fake_dev):
    dev = CharacterDevice("/dev/gpio0")
    data = array("i", [0])

    ret = dev.ioctl_raw(GPIOC_PINTYPE, data)

    assert ret == 0
    assert data[0] == int(GPIOPinType.GPIO_OUTPUT_PIN)


def test_open_oserror_propagates(monkeypatch):
    def fake_open(path, flags):
        raise OSError(2, "No such file")

    monkeypatch.setattr("os.open", fake_open)

    with pytest.raises(OSError):
        CharacterDevice("/dev/notfound")
