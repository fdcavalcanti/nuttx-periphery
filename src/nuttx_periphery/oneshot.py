"""Oneshot timer API for NuttX oneshot character devices.

Wraps the oneshot driver ioctls from ``include/nuttx/timers/oneshot.h``:

- start (delay + signal notification in one ``OSIOC_START`` call)
- cancel
- current time
- maximum delay

Notification uses ``nuttx_periphery.sigevent`` for the embedded
``struct sigevent``. Install a Python handler with ``signal.signal`` before
starting the timer.
"""

from __future__ import annotations

import ctypes
import os
import signal
from dataclasses import dataclass

from .device import CharacterDevice
from .ioctl_consts import OSIOC_CANCEL, OSIOC_CURRENT, OSIOC_MAXDELAY, OSIOC_START
from .sigevent import Sigevent, SigeventStruct, check_signo
from .utils import check_u32


class TimespecStruct(ctypes.Structure):
    _fields_ = [
        ("tv_sec", ctypes.c_int64),
        ("tv_nsec", ctypes.c_long),
    ]


class OneshotStartStruct(ctypes.Structure):
    _fields_ = [
        ("pid", ctypes.c_uint32),
        ("event", SigeventStruct),
        ("ts", TimespecStruct),
    ]


TIMESPEC_SIZE = ctypes.sizeof(TimespecStruct)


@dataclass
class Timespec:
    """NuttX ``struct timespec`` (seconds + nanoseconds).

    ``tv_sec`` is whole seconds; ``tv_nsec`` is nanoseconds (0–999_999_999).
    """

    tv_sec: int
    tv_nsec: int

    @classmethod
    def from_timeout_us(cls, timeout_us: int) -> Timespec:
        """Convert a microsecond delay to ``(tv_sec, tv_nsec)``."""
        check_u32(timeout_us, "timeout_us")
        tv_sec = timeout_us // 1_000_000
        tv_nsec = (timeout_us % 1_000_000) * 1_000
        return cls(tv_sec=tv_sec, tv_nsec=tv_nsec)

    def to_struct(self) -> TimespecStruct:
        return TimespecStruct(tv_sec=self.tv_sec, tv_nsec=self.tv_nsec)

    @classmethod
    def from_struct(cls, ts: TimespecStruct) -> Timespec:
        return cls(tv_sec=int(ts.tv_sec), tv_nsec=int(ts.tv_nsec))


class OneshotTimer(CharacterDevice):
    """NuttX oneshot timer character device (e.g. ``/dev/oneshot``)."""

    def __init__(self, path: str) -> None:
        super().__init__(path)
        self._timeout_us = 1_000_000
        self._signo = signal.SIGUSR1

    def set_timeout_us(self, timeout_us: int) -> None:
        """Configure the delay used by :meth:`start` (microseconds)."""
        check_u32(timeout_us, "timeout_us")
        self._timeout_us = timeout_us

    def set_signo(self, signo: int) -> None:
        """Configure the signal delivered on expiration."""
        check_signo(signo)
        self._signo = signo

    def start(
        self,
        signo: int | None = None,
        *,
        pid: int | None = None,
        timeout_us: int | None = None,
    ) -> None:
        """Start the oneshot timer.

        Uses the configured timeout and signal unless overridden. Delivers
        *signo* to *pid* when the timer expires (defaults to ``os.getpid()``).

        Install a handler for *signo* (for example via ``signal.signal``)
        before calling this method.
        """
        task_pid = os.getpid() if pid is None else pid
        if not isinstance(task_pid, int):
            raise TypeError("pid must be int")
        if task_pid <= 0:
            raise ValueError("pid must be > 0")

        delay_us = self._timeout_us if timeout_us is None else timeout_us
        check_u32(delay_us, "timeout_us")

        notify_signo = self._signo if signo is None else signo
        check_signo(notify_signo)

        event = Sigevent.signal(notify_signo, thread_id=task_pid)
        start_struct = OneshotStartStruct(
            pid=task_pid,
            event=event.to_struct(),
            ts=Timespec.from_timeout_us(delay_us).to_struct(),
        )
        ret = self.ioctl(OSIOC_START, start_struct)
        if ret != 0:
            raise RuntimeError(f"Error starting oneshot timer: {ret}")

    def cancel(self) -> Timespec:
        """Stop the timer and return the time remaining."""
        return self._read_timespec(OSIOC_CANCEL)

    def current(self) -> Timespec:
        """Read the current timer time."""
        return self._read_timespec(OSIOC_CURRENT)

    def max_delay(self) -> Timespec:
        """Read the maximum delay supported by this timer."""
        return self._read_timespec(OSIOC_MAXDELAY)

    def _read_timespec(self, cmd: int) -> Timespec:
        ts = TimespecStruct(tv_sec=0, tv_nsec=0)
        ret = self.ioctl(cmd, ts)
        if ret != 0:
            raise RuntimeError(f"Error reading timespec: {ret}")
        return Timespec.from_struct(ts)


__all__ = [
    "OneshotTimer",
    "Timespec",
]
