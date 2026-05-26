"""Tests for struct sigevent packing."""

from __future__ import annotations

import ctypes
import os

import pytest

from nuttx_periphery.ioctl_consts import SIGEV_SIGNAL
from nuttx_periphery.sigevent import MAX_SIGNO, SIGEVENT_SIZE, Sigevent, check_signo


class _CSigevent(ctypes.Structure):
    _fields_ = [
        ("sigev_notify", ctypes.c_int),
        ("sigev_signo", ctypes.c_int),
        ("sigev_value", ctypes.c_void_p),
        ("_tid", ctypes.c_int),
    ]


def test_sigevent_size_matches_ctypes():
    assert SIGEVENT_SIZE == ctypes.sizeof(_CSigevent)


def test_sigevent_signal_matches_ctypes(monkeypatch):
    monkeypatch.setattr(os, "gettid", lambda: 99, raising=False)
    monkeypatch.setattr(os, "getpid", lambda: 99)

    event = _CSigevent()
    event.sigev_notify = SIGEV_SIGNAL
    event.sigev_signo = 10
    event.sigev_value = None
    event._tid = 99

    assert Sigevent.signal(10).to_bytes() == bytes(event)


def test_sigevent_signal_uses_getpid_without_gettid(monkeypatch):
    monkeypatch.delattr(os, "gettid", raising=False)
    monkeypatch.setattr(os, "getpid", lambda: 42)

    assert Sigevent.signal(10).thread_id == 42


def test_sigevent_roundtrip():
    original = Sigevent.signal(12, value=42, thread_id=7)
    restored = Sigevent.from_bytes(original.to_bytes())

    assert restored == original


def test_sigevent_validation():
    with pytest.raises(ValueError):
        check_signo(0)
    with pytest.raises(ValueError):
        check_signo(MAX_SIGNO + 1)
    with pytest.raises(TypeError):
        Sigevent.signal("1")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        Sigevent(notify=SIGEV_SIGNAL, signo=0).to_bytes()
