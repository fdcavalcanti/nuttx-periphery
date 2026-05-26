"""Tests for struct sigevent packing."""

from __future__ import annotations

import ctypes
import os

import pytest

from nuttx_periphery.ioctl_consts import SIGEV_SIGNAL
from nuttx_periphery.sigevent import (
    MAX_SIGNO,
    SIGEVENT_SIZE,
    SIGVAL_SIZE,
    Sigevent,
    SigeventStruct,
    SigvalStruct,
    check_signo,
)


def _reference_sigevent(
    notify: int,
    signo: int,
    value: int,
    thread_id: int,
) -> bytes:
    sigval = SigvalStruct()
    sigval.sival_int = value

    entry = SigeventStruct()
    entry.sigev_notify = notify
    entry.sigev_signo = signo
    entry.sigev_value = sigval
    entry._tid = thread_id
    return bytes(entry)


def test_sigval_union_size():
    assert SIGVAL_SIZE == ctypes.sizeof(ctypes.c_void_p)
    assert ctypes.sizeof(SigvalStruct) == SIGVAL_SIZE


def test_sigval_int_and_ptr_share_storage():
    slot = SigvalStruct()
    slot.sival_int = 42
    assert slot.sival_int == 42
    assert slot.sival_ptr == 42


def test_sigevent_struct_size():
    assert ctypes.sizeof(SigeventStruct) == SIGEVENT_SIZE
    assert SIGEVENT_SIZE >= SIGVAL_SIZE + 3 * ctypes.sizeof(ctypes.c_int)


def test_sigevent_signal_default_layout(monkeypatch):
    monkeypatch.setattr(os, "getpid", lambda: 99)

    expected = _reference_sigevent(SIGEV_SIGNAL, 10, 0, 99)
    assert Sigevent.signal(10).to_bytes() == expected


def test_sigevent_signal_uses_getpid(monkeypatch):
    monkeypatch.setattr(os, "getpid", lambda: 42)

    assert Sigevent.signal(10).thread_id == 42
    assert Sigevent.signal(10).to_bytes() == _reference_sigevent(
        SIGEV_SIGNAL, 10, 0, 42
    )


def test_sigevent_roundtrip():
    original = Sigevent.signal(12, value=42, thread_id=7)
    restored = Sigevent.from_bytes(original.to_bytes())

    assert restored == original


def test_sigevent_from_memoryview():
    payload = Sigevent.signal(5, value=3, thread_id=1).to_bytes()
    view = memoryview(payload)

    restored = Sigevent.from_bytes(view)
    assert restored.signo == 5
    assert restored.value == 3
    assert restored.thread_id == 1


def test_sigevent_validation():
    with pytest.raises(ValueError):
        check_signo(0)
    with pytest.raises(ValueError):
        check_signo(MAX_SIGNO + 1)
    with pytest.raises(TypeError):
        Sigevent.signal("1")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        Sigevent(notify=SIGEV_SIGNAL, signo=0)
    with pytest.raises(ValueError):
        Sigevent.from_bytes(b"\x00" * (SIGEVENT_SIZE - 1))
    with pytest.raises(TypeError):
        Sigevent.from_bytes(123)  # type: ignore[arg-type]
