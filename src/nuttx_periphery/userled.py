"""User LED API for NuttX LED character devices."""

from __future__ import annotations

import struct
from array import array

from .device import CharacterDevice
from .ioctl_consts import (
    ULEDIOC_GETALL,
    ULEDIOC_SETALL,
    ULEDIOC_SETLED,
    ULEDIOC_SUPPORTED,
)


class UserLED(CharacterDevice):
    """NuttX user LED character device wrapper."""

    def supported(self) -> int:
        """Return bitmask of LEDs supported by the hardware."""
        led_mask = array("I", [0])
        self.ioctl(ULEDIOC_SUPPORTED, led_mask)
        return int(led_mask[0])

    def get_all(self) -> int:
        """Return current LED state bitmask."""
        led_mask = array("I", [0])
        self.ioctl(ULEDIOC_GETALL, led_mask)
        return int(led_mask[0])

    def set_all(self, led_mask: int) -> None:
        """Set all LED states from a bitmask."""
        if not isinstance(led_mask, int):
            raise TypeError("led_mask must be int")
        if led_mask < 0:
            raise ValueError("led_mask must be >= 0")
        self.ioctl(ULEDIOC_SETALL, led_mask)

    def set_led(self, led: int, on: bool) -> None:
        """Set a single LED by index."""
        if not isinstance(led, int):
            raise TypeError("led must be int")
        if led < 0:
            raise ValueError("led must be >= 0")
        if not isinstance(on, bool):
            raise TypeError("on must be bool")

        # struct userled_s { uint8_t ul_led; bool ul_on; }
        payload = bytearray(struct.pack("@BB", led & 0xFF, int(on)))
        self.ioctl(ULEDIOC_SETLED, payload)


__all__ = ["UserLED"]
