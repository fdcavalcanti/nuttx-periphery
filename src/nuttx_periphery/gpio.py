"""GPIO API for NuttX character GPIO devices."""

from __future__ import annotations

from array import array
from enum import IntEnum

from .device import CharacterDevice
from .ioctl_consts import (
    GPIOC_IRQ_SETMASK,
    GPIOC_PINTYPE,
    GPIOC_READ,
    GPIOC_REGISTER,
    GPIOC_SETDEBOUNCE,
    GPIOC_SETPINTYPE,
    GPIOC_UNREGISTER,
    GPIOC_WRITE,
)


class GPIOPinType(IntEnum):
    """Pin types mirrored from include/nuttx/ioexpander/gpio.h."""

    GPIO_INPUT_PIN = 0
    GPIO_INPUT_PIN_PULLUP = 1
    GPIO_INPUT_PIN_PULLDOWN = 2
    GPIO_OUTPUT_PIN = 3
    GPIO_OUTPUT_PIN_OPENDRAIN = 4
    GPIO_INTERRUPT_PIN = 5
    GPIO_INTERRUPT_HIGH_PIN = 6
    GPIO_INTERRUPT_LOW_PIN = 7
    GPIO_INTERRUPT_RISING_PIN = 8
    GPIO_INTERRUPT_FALLING_PIN = 9
    GPIO_INTERRUPT_BOTH_PIN = 10
    GPIO_INTERRUPT_PIN_WAKEUP = 11
    GPIO_INTERRUPT_HIGH_PIN_WAKEUP = 12
    GPIO_INTERRUPT_LOW_PIN_WAKEUP = 13
    GPIO_INTERRUPT_RISING_PIN_WAKEUP = 14
    GPIO_INTERRUPT_FALLING_PIN_WAKEUP = 15
    GPIO_INTERRUPT_BOTH_PIN_WAKEUP = 16


class GPIO(CharacterDevice):
    """NuttX GPIO character device wrapper."""

    def read(self) -> bool:
        """Read current GPIO level."""
        value = bytearray(1)
        self.ioctl(GPIOC_READ, value)
        return bool(value[0])

    def write(self, value: bool) -> None:
        """Write output GPIO level."""
        if not isinstance(value, bool):
            raise TypeError("value must be bool")
        self.ioctl(GPIOC_WRITE, int(value))

    def get_pin_type(self) -> GPIOPinType:
        """Get current configured pin type."""
        result = array("i", [0])
        self.ioctl(GPIOC_PINTYPE, result)
        return GPIOPinType(result[0])

    def set_pin_type(self, pin_type: GPIOPinType) -> None:
        """Set GPIO pin type."""
        if isinstance(pin_type, GPIOPinType):
            value = int(pin_type)
        elif isinstance(pin_type, int):
            value = pin_type
        else:
            raise TypeError("pin_type must be GPIOPinType or int")

        self.ioctl(GPIOC_SETPINTYPE, value)

    def set_debounce_ns(self, value: int) -> None:
        """Set debounce duration in nanoseconds."""
        if not isinstance(value, int):
            raise TypeError("value must be int")
        if value < 0:
            raise ValueError("value must be >= 0")
        self.ioctl(GPIOC_SETDEBOUNCE, value)

    def set_irq_mask(self, masked: bool) -> None:
        """Mask or unmask GPIO interrupt."""
        if not isinstance(masked, bool):
            raise TypeError("masked must be bool")
        self.ioctl(GPIOC_IRQ_SETMASK, int(masked))

    def register_signal(self, signo: int) -> None:
        """Register a signal to be emitted by GPIO interrupt."""
        if not isinstance(signo, int):
            raise TypeError("signo must be int")
        if signo <= 0:
            raise ValueError("signo must be > 0")
        self.ioctl(GPIOC_REGISTER, signo)

    def unregister_signal(self) -> None:
        """Disable GPIO interrupt signal registration."""
        self.ioctl(GPIOC_UNREGISTER, 0)


__all__ = ["GPIO", "GPIOPinType"]
