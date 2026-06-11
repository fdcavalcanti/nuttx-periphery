"""NuttX ``struct sigevent`` helpers for signal-based device notifications.

Mirrors ``include/signal.h`` for the common case (``SIGEV_SIGNAL`` and
``_sigev_un._tid``). ``CONFIG_SIG_EVTHREAD`` (notify function + pthread
attributes) is **not** supported.

Layout (ctypes):

- ``SigvalStruct`` — ``union sigval`` (``sival_int`` / ``sival_ptr`` share storage)
- ``SigeventStruct`` — full C struct for binary ioctl payloads
- ``Sigevent`` — dataclass wrapper with validation and pack/unpack

Typical use: build a ``Sigevent``, call ``to_bytes()``, pass the buffer to an
ioctl such as ``GPIOC_REGISTER`` or embed it in ``struct timer_notify_s``.

Signal numbers must be **1–63** on NuttX (see ``MAX_SIGNO``).
"""

from __future__ import annotations

import ctypes
import os
from dataclasses import dataclass

from .ioctl_consts import SIGEV_SIGNAL

MAX_SIGNO = 63


class SigvalStruct(ctypes.Union):
    """``union sigval`` — integer or pointer payload for notifications."""

    _fields_ = [
        ("sival_int", ctypes.c_int),
        ("sival_ptr", ctypes.c_void_p),
    ]


class SigeventStruct(ctypes.Structure):
    """``struct sigevent`` (no ``CONFIG_SIG_EVTHREAD``)."""

    _fields_ = [
        ("sigev_notify", ctypes.c_int),
        ("sigev_signo", ctypes.c_int),
        ("sigev_value", SigvalStruct),
        ("_tid", ctypes.c_int),
    ]


@dataclass
class Sigevent:
    """High-level view of NuttX ``struct sigevent``.

    Attributes:
        notify: ``sigev_notify`` (e.g. ``SIGEV_SIGNAL``).
        signo: Signal number delivered to the task (1–63).
        value: Written to ``sigev_value.sival_int`` (0 if unused).
        thread_id: ``_sigev_un._tid`` (target task/thread id).
    """

    notify: int = SIGEV_SIGNAL
    signo: int = 0
    value: int = 0
    thread_id: int = 0

    def __post_init__(self) -> None:
        check_signo(self.signo)
        for name, val in (
            ("notify", self.notify),
            ("value", self.value),
            ("thread_id", self.thread_id),
        ):
            if not isinstance(val, int):
                raise TypeError(f"{name} must be int")

    @classmethod
    def signal(
        cls,
        signo: int,
        *,
        notify: int = SIGEV_SIGNAL,
        value: int = 0,
        thread_id: int | None = None,
    ) -> Sigevent:
        """Build a signal notification for *signo*.

        When *thread_id* is omitted, ``os.getpid()`` is used for ``_tid``.
        """
        check_signo(signo)
        tid = os.getpid() if thread_id is None else thread_id
        return cls(
            notify=notify,
            signo=signo,
            value=value,
            thread_id=tid,
        )

    def to_struct(self) -> SigeventStruct:
        sigval = SigvalStruct()
        sigval.sival_int = self.value

        sigevent = SigeventStruct()
        sigevent.sigev_notify = self.notify
        sigevent.sigev_signo = self.signo
        sigevent.sigev_value = sigval
        sigevent._tid = self.thread_id
        return sigevent

    def to_bytes(self) -> bytes:
        """Pack as a native ``struct sigevent`` buffer (``SIGEVENT_SIZE`` bytes)."""
        return bytes(self.to_struct())

    @classmethod
    def from_bytes(cls, data: bytes | bytearray | memoryview) -> Sigevent:
        """Parse a ``struct sigevent`` buffer of at least ``SIGEVENT_SIZE`` bytes."""
        if not isinstance(data, (bytes, bytearray, memoryview)):
            raise TypeError("data must be bytes, bytearray, or memoryview")
        if len(data) < ctypes.sizeof(SigeventStruct):
            raise ValueError("data buffer too small for struct sigevent")

        sigevent = SigeventStruct.from_buffer_copy(
            bytes(data[: ctypes.sizeof(SigeventStruct)])
        )
        return cls(
            notify=sigevent.sigev_notify,
            signo=sigevent.sigev_signo,
            value=sigevent.sigev_value.sival_int,
            thread_id=sigevent._tid,
        )


def check_signo(signo: int) -> None:
    """Raise if *signo* is not a valid NuttX signal number (1–63)."""
    if not isinstance(signo, int):
        raise TypeError("signo must be int")
    if signo < 1 or signo > MAX_SIGNO:
        raise ValueError(f"signo must be between 1 and {MAX_SIGNO}")


SIGEVENT_SIZE = ctypes.sizeof(SigeventStruct)
SIGVAL_SIZE = ctypes.sizeof(SigvalStruct)

__all__ = [
    "MAX_SIGNO",
    "SIGEVENT_SIZE",
    "SIGVAL_SIZE",
    "Sigevent",
    "SigeventStruct",
    "SigvalStruct",
    "check_signo",
]
