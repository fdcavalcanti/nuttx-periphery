"""Timer API for NuttX timer character devices."""

from __future__ import annotations

import ctypes
import os
import struct
from array import array
from dataclasses import dataclass

from .device import CharacterDevice
from .ioctl_consts import (
    SIGEV_SIGNAL,
    TCFLAGS_ACTIVE,
    TCFLAGS_HANDLER,
    TCIOC_GETSTATUS,
    TCIOC_MAXTIMEOUT,
    TCIOC_NOTIFICATION,
    TCIOC_SETTIMEOUT,
    TCIOC_START,
    TCIOC_STOP,
    TCIOC_TICK_GETSTATUS,
    TCIOC_TICK_MAXTIMEOUT,
    TCIOC_TICK_SETTIMEOUT,
)
from .utils import check_u32

_MAX_SIGNO = 63


class _Sigevent(ctypes.Structure):
    """struct sigevent from include/signal.h."""

    _fields_ = [
        ("sigev_notify", ctypes.c_int),
        ("sigev_signo", ctypes.c_int),
        ("sigev_value", ctypes.c_void_p),
        ("_tid", ctypes.c_int),
    ]


class _TimerNotify(ctypes.Structure):
    """struct timer_notify_s from include/nuttx/timers/timer.h."""

    _fields_ = [
        ("event", _Sigevent),
        ("pid", ctypes.c_int),
        ("periodic", ctypes.c_bool),
    ]


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


def pack_timer_notify(
    signo: int,
    *,
    pid: int,
    periodic: bool = False,
    notify: int = SIGEV_SIGNAL,
) -> bytes:
    """Pack a ``timer_notify_s`` buffer for ``TCIOC_NOTIFICATION``."""
    _check_signo(signo)
    _check_pid(pid)
    if not isinstance(notify, int):
        raise TypeError("notify must be int")
    if not isinstance(periodic, bool):
        raise TypeError("periodic must be bool")

    entry = _TimerNotify()
    entry.event.sigev_notify = notify
    entry.event.sigev_signo = signo
    entry.event.sigev_value = None
    entry.event._tid = 0
    entry.pid = pid
    entry.periodic = periodic
    return bytes(entry)


def _check_signo(signo: int) -> None:
    if not isinstance(signo, int):
        raise TypeError("signo must be int")
    if signo < 1 or signo > _MAX_SIGNO:
        raise ValueError(f"signo must be between 1 and {_MAX_SIGNO}")


def _check_pid(pid: int) -> None:
    if not isinstance(pid, int):
        raise TypeError("pid must be int")
    if pid <= 0:
        raise ValueError("pid must be > 0")


class Timer(CharacterDevice):
    """NuttX timer character device wrapper."""

    def start(self) -> None:
        """Start the timer."""
        self.ioctl(TCIOC_START, 0)

    def stop(self) -> None:
        """Stop the timer."""
        self.ioctl(TCIOC_STOP, 0)

    def set_timeout_us(self, timeout_us: int) -> None:
        """Set the timer period in microseconds."""
        check_u32(timeout_us, "timeout_us")
        self.ioctl(TCIOC_SETTIMEOUT, timeout_us)

    def get_status_us(self) -> TimerStatus:
        """Read current timer status with time values in microseconds."""
        return self.read_status(TCIOC_GETSTATUS)

    def max_timeout_us(self) -> int:
        """Read the maximum supported timeout in microseconds."""
        return self._read_u32(TCIOC_MAXTIMEOUT)

    def set_timeout_ticks(self, timeout_ticks: int) -> None:
        """Set the timer period in ticks."""
        check_u32(timeout_ticks, "timeout_ticks")
        self.ioctl(TCIOC_TICK_SETTIMEOUT, timeout_ticks)

    def get_status_ticks(self) -> TimerStatus:
        """Read current timer status with time values in ticks."""
        return self.read_status(TCIOC_TICK_GETSTATUS)

    def max_timeout_ticks(self) -> int:
        """Read the maximum supported timeout in ticks."""
        return self._read_u32(TCIOC_TICK_MAXTIMEOUT)

    def is_active(self) -> bool:
        """Return True if the timer is currently running."""
        return self.get_status_us().active

    def set_notification(
        self,
        signo: int,
        *,
        pid: int | None = None,
        periodic: bool = False,
        notify: int = SIGEV_SIGNAL,
    ) -> None:
        """Register a signal to receive when the timer expires.

        Install a handler for ``signo`` (for example via ``signal.signal``)
        before starting the timer. The NuttX timer example uses
        ``sigaction`` plus ``TCIOC_NOTIFICATION`` in that order.

        Args:
            signo: NuttX signal number delivered on expiration (1–63).
            pid: Task ID to signal; defaults to ``os.getpid()``.
            periodic: When True, the timer rearms after each expiration.
            notify: ``sigev_notify`` mode; use ``SIGEV_SIGNAL`` (default).
        """
        task_pid = os.getpid() if pid is None else pid
        payload = pack_timer_notify(
            signo,
            pid=task_pid,
            periodic=periodic,
            notify=notify,
        )
        ret = self.ioctl(TCIOC_NOTIFICATION, bytearray(payload))
        if ret != 0:
            raise RuntimeError(f"Error setting notification: {ret}")

    def read_status(self, cmd: int) -> TimerStatus:
        """Read timer status via the given TCIOC_GETSTATUS ioctl command."""
        buf = bytearray(_STATUS_SIZE)
        ret = self.ioctl(cmd, buf)
        if ret != 0:
            raise RuntimeError(f"Error reading status: {ret}")
        return TimerStatus.from_bytes(buf)

    def _read_u32(self, cmd: int) -> int:
        result = array("I", [0])
        ret = self.ioctl(cmd, result)
        if ret != 0:
            raise RuntimeError(f"Error reading u32: {ret}")
        return int(result[0])


__all__ = [
    "Timer",
    "TimerStatus",
    "pack_timer_notify",
]
