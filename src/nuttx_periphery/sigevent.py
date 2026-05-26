"""NuttX ``struct sigevent`` helpers for signal-based device notifications."""

from __future__ import annotations

import ctypes
import os
import struct
from dataclasses import dataclass

from .ioctl_consts import SIGEV_SIGNAL

MAX_SIGNO = 63

_POINTER_SIZE = ctypes.sizeof(ctypes.c_void_p)
if _POINTER_SIZE == 4:
    _SIGEVENT_STRUCT = struct.Struct("@iiii")
elif _POINTER_SIZE == 8:
    _SIGEVENT_STRUCT = struct.Struct("@iiQi4x")
else:
    raise RuntimeError(f"Unsupported pointer size: {_POINTER_SIZE}")

SIGEVENT_SIZE = _SIGEVENT_STRUCT.size


@dataclass
class Sigevent:
    """NuttX ``struct sigevent`` from include/signal.h.

    Fields mirror ``sigev_notify``, ``sigev_signo``, ``sigev_value`` (as an
    integer; use 0 when unused), and ``sigev_notify_thread_id`` (``_tid``).
    """

    notify: int = SIGEV_SIGNAL
    signo: int = 0
    value: int = 0
    thread_id: int = 0

    @classmethod
    def signal(
        cls,
        signo: int,
        *,
        notify: int = SIGEV_SIGNAL,
        value: int = 0,
        thread_id: int | None = None,
    ) -> Sigevent:
        """Build a ``SIGEV_SIGNAL`` notification for *signo*.

        When *thread_id* is omitted, ``os.getpid()`` is used.
        """
        check_signo(signo)
        tid = os.getpid() if thread_id is None else thread_id
        return cls(
            notify=notify,
            signo=signo,
            value=value,
            thread_id=tid,
        )

    def to_bytes(self) -> bytes:
        """Pack this instance as a NuttX ``struct sigevent`` buffer."""
        check_signo(self.signo)
        for name, val in (
            ("notify", self.notify),
            ("value", self.value),
            ("thread_id", self.thread_id),
        ):
            if not isinstance(val, int):
                raise TypeError(f"{name} must be int")

        return _SIGEVENT_STRUCT.pack(
            self.notify,
            self.signo,
            self.value,
            self.thread_id,
        )

    @classmethod
    def from_bytes(cls, data: bytes | bytearray | memoryview) -> Sigevent:
        """Parse a ``struct sigevent`` buffer."""
        if not isinstance(data, (bytes, bytearray, memoryview)):
            raise TypeError("data must be bytes, bytearray, or memoryview")
        if len(data) < SIGEVENT_SIZE:
            raise ValueError("data buffer too small for struct sigevent")

        notify, signo, value, thread_id = _SIGEVENT_STRUCT.unpack_from(data)
        return cls(
            notify=notify,
            signo=signo,
            value=value,
            thread_id=thread_id,
        )


def check_signo(signo: int) -> None:
    if not isinstance(signo, int):
        raise TypeError("signo must be int")
    if signo < 1 or signo > MAX_SIGNO:
        raise ValueError(f"signo must be between 1 and {MAX_SIGNO}")


__all__ = [
    "MAX_SIGNO",
    "SIGEVENT_SIZE",
    "Sigevent",
    "check_signo",
]
