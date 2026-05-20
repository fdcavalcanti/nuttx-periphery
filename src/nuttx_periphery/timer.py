"""Timer API for NuttX timer character devices."""

from __future__ import annotations

import ctypes
import os
import struct
from array import array
from dataclasses import dataclass

from .device import CharacterDevice
from .ioctl_consts import (
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

# sigev_notify values from include/signal.h
SIGEV_NONE = 0
SIGEV_SIGNAL = 1
SIGEV_THREAD_ID = 4

# struct timer_status_s { uint32_t flags; uint32_t timeout; uint32_t timeleft; }
_STATUS_STRUCT = struct.Struct("@III")
_STATUS_SIZE = _STATUS_STRUCT.size


# struct sigevent and struct timer_notify_s mirrored from include/signal.h
# and include/nuttx/timers/timer.h. The CONFIG_SIG_EVTHREAD variant is not
# represented; the union is reduced to its non-thread member (_tid).
class _SigvalUnion(ctypes.Union):
    _fields_ = [
        ("sival_int", ctypes.c_int),
        ("sival_ptr", ctypes.c_void_p),
    ]


class _SigevUnUnion(ctypes.Union):
    _fields_ = [("_tid", ctypes.c_int)]


class _SigEventStruct(ctypes.Structure):
    _fields_ = [
        ("sigev_notify", ctypes.c_int),
        ("sigev_signo", ctypes.c_int),
        ("sigev_value", _SigvalUnion),
        ("_sigev_un", _SigevUnUnion),
    ]


class _TimerNotifyStruct(ctypes.Structure):
    _fields_ = [
        ("event", _SigEventStruct),
        ("pid", ctypes.c_int),
        ("periodic", ctypes.c_bool),
    ]


_NOTIFY_SIZE = ctypes.sizeof(_TimerNotifyStruct)


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


@dataclass
class TimerNotify:
    """NuttX timer_notify_s structure.

    Describes how the kernel notifies user space when the timer expires.
    The CONFIG_SIG_EVTHREAD variant of struct sigevent is not supported.

    Attributes:
        pid: Task/thread ID to receive the signal.
        signo: Signal number to deliver (e.g. SIGRTMIN..SIGRTMAX).
        periodic: True for periodic notifications, False for one-shot.
        notify: Notification method (SIGEV_NONE, SIGEV_SIGNAL,
            SIGEV_THREAD_ID). Defaults to SIGEV_SIGNAL.
        sigval_int: Integer payload delivered with the signal (sigval.sival_int).
        tid: Target thread id when notify == SIGEV_THREAD_ID.
    """

    pid: int
    signo: int
    periodic: bool = True
    notify: int = SIGEV_SIGNAL
    sigval_int: int = 0
    tid: int = 0

    def to_bytes(self) -> bytes:
        if not isinstance(self.pid, int):
            raise TypeError("pid must be int")
        if not isinstance(self.signo, int):
            raise TypeError("signo must be int")
        if not isinstance(self.periodic, bool):
            raise TypeError("periodic must be bool")

        c_obj = _TimerNotifyStruct()
        c_obj.event.sigev_notify = self.notify
        c_obj.event.sigev_signo = self.signo
        c_obj.event.sigev_value.sival_int = self.sigval_int
        c_obj.event._sigev_un._tid = self.tid
        c_obj.pid = self.pid
        c_obj.periodic = self.periodic
        return bytes(c_obj)

    @classmethod
    def from_bytes(cls, data: bytes | bytearray | memoryview) -> "TimerNotify":
        if not isinstance(data, (bytes, bytearray, memoryview)):
            raise TypeError("data must be bytes, bytearray, or memoryview")
        if len(data) < _NOTIFY_SIZE:
            raise ValueError("data buffer too small for timer_notify_s")
        c_obj = _TimerNotifyStruct.from_buffer_copy(bytes(data[:_NOTIFY_SIZE]))
        return cls(
            pid=int(c_obj.pid),
            signo=int(c_obj.event.sigev_signo),
            periodic=bool(c_obj.periodic),
            notify=int(c_obj.event.sigev_notify),
            sigval_int=int(c_obj.event.sigev_value.sival_int),
            tid=int(c_obj.event._sigev_un._tid),
        )


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
        return self._read_status(TCIOC_GETSTATUS)

    def max_timeout_us(self) -> int:
        """Read the maximum supported timeout in microseconds."""
        return self._read_u32(TCIOC_MAXTIMEOUT)

    def set_timeout_ticks(self, timeout_ticks: int) -> None:
        """Set the timer period in ticks."""
        check_u32(timeout_ticks, "timeout_ticks")
        self.ioctl_raw(TCIOC_TICK_SETTIMEOUT, timeout_ticks)

    def get_status_ticks(self) -> TimerStatus:
        """Read current timer status with time values in ticks."""
        return self._read_status(TCIOC_TICK_GETSTATUS)

    def max_timeout_ticks(self) -> int:
        """Read the maximum supported timeout in ticks."""
        return self._read_u32(TCIOC_TICK_MAXTIMEOUT)

    def is_active(self) -> bool:
        """Return True if the timer is currently running."""
        return self.get_status_us().active

    def set_notification(
        self,
        notify: TimerNotify | bytes | bytearray | memoryview,
    ) -> None:
        """Register the timer expiration notification (TCIOC_NOTIFICATION)."""
        if isinstance(notify, TimerNotify):
            notify = notify.to_bytes()
        elif not isinstance(notify, (bytes, bytearray, memoryview)):
            raise TypeError(
                "notify must be TimerNotify, bytes, bytearray, or memoryview"
            )
        self.ioctl_raw(TCIOC_NOTIFICATION, notify)

    def notify_signal(
        self,
        signo: int,
        periodic: bool = True,
        pid: int | None = None,
        sigval_int: int = 0,
    ) -> None:
        """Configure signal-based notification for the calling process.

        Defaults pid to os.getpid(). Use signal.signal() or
        signal.sigwaitinfo() to receive the signal in Python.
        """
        if not isinstance(signo, int):
            raise TypeError("signo must be int")
        if signo <= 0:
            raise ValueError("signo must be > 0")
        if pid is None:
            pid = os.getpid()
        self.set_notification(
            TimerNotify(
                pid=pid,
                signo=signo,
                periodic=periodic,
                notify=SIGEV_SIGNAL,
                sigval_int=sigval_int,
            )
        )

    def _read_status(self, cmd: int) -> TimerStatus:
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
    "TimerNotify",
    "SIGEV_NONE",
    "SIGEV_SIGNAL",
    "SIGEV_THREAD_ID",
]
