"""Timer API for NuttX timer character devices.

Wraps the timer driver ioctls from ``include/nuttx/timers/timer.h``:

- start / stop
- timeout in microseconds or ticks
- status (`struct timer_status_s`) via ``TimerStatus``
- signal notification (`struct timer_notify_s`) via ``set_notification``

Notification uses ``nuttx_periphery.sigevent`` for the embedded
``struct sigevent``. Install a Python handler with ``signal.signal`` before
starting the timer.
"""

from __future__ import annotations

import ctypes
import os
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
from .sigevent import Sigevent, SigeventStruct, check_signo
from .utils import check_u32


class TimerStatusStruct(ctypes.Structure):
    _fields_ = [
        ("flags", ctypes.c_uint32),
        ("timeout", ctypes.c_uint32),
        ("timeleft", ctypes.c_uint32),
    ]


class TimerNotifyStruct(ctypes.Structure):
    _fields_ = [
        ("event", SigeventStruct),
        ("pid", ctypes.c_int),
        ("periodic", ctypes.c_bool),
    ]


TIMER_NOTIFY_SIZE = ctypes.sizeof(TimerNotifyStruct)
TIMER_STATUS_SIZE = ctypes.sizeof(TimerStatusStruct)


@dataclass
class TimerNotify:
    """``struct timer_notify_s`` (sigevent + pid + periodic).

    Use :meth:`signal` and :meth:`to_bytes` for the ``TCIOC_NOTIFICATION`` payload.
    """

    event: Sigevent
    pid: int
    periodic: bool = False

    SIZE: int = TIMER_NOTIFY_SIZE

    @classmethod
    def signal(
        cls,
        signo: int,
        *,
        pid: int,
        periodic: bool = False,
        notify: int = SIGEV_SIGNAL,
    ) -> TimerNotify:
        """Build a signal notification for ``TCIOC_NOTIFICATION``."""
        check_signo(signo)
        if not isinstance(notify, int):
            raise TypeError("notify must be int")
        if not isinstance(periodic, bool):
            raise TypeError("periodic must be bool")
        if not isinstance(pid, int):
            raise TypeError("pid must be int")
        if pid <= 0:
            raise ValueError("pid must be > 0")

        return cls(
            event=Sigevent(notify=notify, signo=signo, value=0, thread_id=0),
            pid=pid,
            periodic=periodic,
        )

    def to_bytes(self) -> bytes:
        timer_notify = TimerNotifyStruct()
        timer_notify.event = SigeventStruct.from_buffer_copy(self.event.to_bytes())
        timer_notify.pid = self.pid
        timer_notify.periodic = self.periodic
        return bytes(timer_notify)

    @classmethod
    def from_bytes(cls, data: bytes | bytearray | memoryview) -> TimerNotify:
        """Parse a ``struct timer_notify_s`` buffer."""
        if not isinstance(data, (bytes, bytearray, memoryview)):
            raise TypeError("data must be bytes, bytearray, or memoryview")
        if len(data) < TIMER_NOTIFY_SIZE:
            raise ValueError("data buffer too small for timer_notify_s")
        timer_notify = TimerNotifyStruct.from_buffer_copy(
            bytes(data[:TIMER_NOTIFY_SIZE])
        )
        return cls(
            event=Sigevent.from_bytes(bytes(timer_notify.event)),
            pid=timer_notify.pid,
            periodic=bool(timer_notify.periodic),
        )


@dataclass
class TimerStatus:
    """NuttX timer status structure.

    Time values are in the unit returned by the issuing ioctl:
    microseconds for TCIOC_GETSTATUS / TCIOC_MAXTIMEOUT, ticks for
    TCIOC_TICK_GETSTATUS / TCIOC_TICK_MAXTIMEOUT.

    ``flags`` is a status bitmask (``TCFLAGS_ACTIVE``, ``TCFLAGS_HANDLER``).
    ``timeout`` is the configured timer period; ``timeleft`` is time remaining
    until the next expiration.
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
        timer_status = TimerStatusStruct()
        timer_status.flags = self.flags
        timer_status.timeout = self.timeout
        timer_status.timeleft = self.timeleft

        return bytes(timer_status)

    @classmethod
    def from_bytes(cls, data: bytes | bytearray | memoryview) -> TimerStatus:
        if not isinstance(data, (bytes, bytearray, memoryview)):
            raise TypeError("data must be bytes, bytearray, or memoryview")
        if len(data) < TIMER_STATUS_SIZE:
            raise ValueError("data buffer too small for timer_status_s")
        timer_status = TimerStatusStruct.from_buffer_copy(
            bytes(data[:TIMER_STATUS_SIZE])
        )
        return cls(
            flags=int(timer_status.flags),
            timeout=int(timer_status.timeout),
            timeleft=int(timer_status.timeleft),
        )


class Timer(CharacterDevice):
    """NuttX timer character device (e.g. ``/dev/timer0``)."""

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
        payload = TimerNotify.signal(
            signo, pid=task_pid, periodic=periodic, notify=notify
        ).to_bytes()
        ret = self.ioctl(TCIOC_NOTIFICATION, bytearray(payload))
        if ret != 0:
            raise RuntimeError(f"Error setting notification: {ret}")

    def read_status(self, cmd: int) -> TimerStatus:
        """Read status using ``TCIOC_GETSTATUS`` or ``TCIOC_TICK_GETSTATUS``."""
        buf = bytearray(TIMER_STATUS_SIZE)
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
    "TimerNotify",
    "TimerStatus",
]
