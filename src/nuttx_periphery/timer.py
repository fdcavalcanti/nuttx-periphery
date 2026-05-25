"""Timer API for NuttX timer character devices."""

from __future__ import annotations

import struct
from array import array
from dataclasses import dataclass

from .device import CharacterDevice
from .ioctl_consts import (
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
from .utils import check_u32

# struct timer_status_s { uint32_t flags; uint32_t timeout; uint32_t timeleft; }
_STATUS_STRUCT = struct.Struct("@III")
_STATUS_SIZE = _STATUS_STRUCT.size


@dataclass
class TimerStatus:
    """NuttX timer status structure.

    Time values are in the unit returned by the issuing ioctl:
    microseconds for TCIOC_GETSTATUS / TCIOC_MAXTIMEOUT, ticks for
    TCIOC_TICK_GETSTATUS / TCIOC_TICK_MAXTIMEOUT.

    Attributes:
        flags: Status bitmask (TCFLAGS_ACTIVE, TCFLAGS_HANDLER).
        timeout: Configured timer period.
        timeleft: Time remaining until next expiration.
    """

    flags: int
    timeout: int
    timeleft: int

    @property
    def active(self) -> bool:
        """True when the timer is currently running."""
        return bool(self.flags & TCFLAGS_ACTIVE)

    @property
    def has_handler(self) -> bool:
        """True when a notification handler is registered."""
        return bool(self.flags & TCFLAGS_HANDLER)

    def to_bytes(self) -> bytes:
        return _STATUS_STRUCT.pack(self.flags, self.timeout, self.timeleft)

    @classmethod
    def from_bytes(cls, data: bytes | bytearray | memoryview) -> "TimerStatus":
        if not isinstance(data, (bytes, bytearray, memoryview)):
            raise TypeError("data must be bytes, bytearray, or memoryview")
        if len(data) < _STATUS_SIZE:
            raise ValueError("data buffer too small for timer_status_s")
        flags, timeout, timeleft = _STATUS_STRUCT.unpack_from(data)
        return cls(flags=flags, timeout=timeout, timeleft=timeleft)


class Timer(CharacterDevice):
    """NuttX timer character device wrapper."""

    def start(self) -> None:
        """Start the timer."""
        self.ioctl_raw(TCIOC_START, 0)

    def stop(self) -> None:
        """Stop the timer."""
        self.ioctl_raw(TCIOC_STOP, 0)

    def set_timeout_us(self, timeout_us: int) -> None:
        """Set the timer period in microseconds."""
        check_u32(timeout_us, "timeout_us")
        self.ioctl_raw(TCIOC_SETTIMEOUT, timeout_us)

    def get_status_us(self) -> TimerStatus:
        """Read current timer status with time values in microseconds."""
        return self.read_status(TCIOC_GETSTATUS)

    def max_timeout_us(self) -> int:
        """Read the maximum supported timeout in microseconds."""
        return self._read_u32(TCIOC_MAXTIMEOUT)

    def set_timeout_ticks(self, timeout_ticks: int) -> None:
        """Set the timer period in ticks."""
        check_u32(timeout_ticks, "timeout_ticks")
        self.ioctl_raw(TCIOC_TICK_SETTIMEOUT, timeout_ticks)

    def get_status_ticks(self) -> TimerStatus:
        """Read current timer status with time values in ticks."""
        return self.read_status(TCIOC_TICK_GETSTATUS)

    def max_timeout_ticks(self) -> int:
        """Read the maximum supported timeout in ticks."""
        return self._read_u32(TCIOC_TICK_MAXTIMEOUT)

    def is_active(self) -> bool:
        """Return True if the timer is currently running."""
        return self.get_status_us().active

    def read_status(self, cmd: int) -> TimerStatus:
        """Read timer status via the given TCIOC_GETSTATUS ioctl command."""
        buf = bytearray(_STATUS_SIZE)
        self.ioctl_raw(cmd, buf)
        return TimerStatus.from_bytes(buf)

    def _read_u32(self, cmd: int) -> int:
        result = array("I", [0])
        self.ioctl_raw(cmd, result)
        return int(result[0])


__all__ = [
    "Timer",
    "TimerStatus",
]
