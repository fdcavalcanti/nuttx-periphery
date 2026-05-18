"""Shared utility helpers for nuttx_periphery."""

from __future__ import annotations

import os


def check_u32(value: int, name: str) -> None:
    if not isinstance(value, int):
        raise TypeError(f"{name} must be int")
    if value < 0 or value > 0xFFFFFFFF:
        raise ValueError(f"{name} must be between 0 and 0xFFFFFFFF")


def check_u8(value: int, name: str) -> None:
    if not isinstance(value, int):
        raise TypeError(f"{name} must be int")
    if value < 0 or value > 0xFF:
        raise ValueError(f"{name} must be between 0 and 0xFF")


def check_i8(value: int, name: str) -> None:
    if not isinstance(value, int):
        raise TypeError(f"{name} must be int")
    if value < -128 or value > 127:
        raise ValueError(f"{name} must be between -128 and 127")


def read_into(path: str, buffer: bytearray | memoryview, size: int) -> int:
    """Open a file, read up to ``size`` bytes into ``buffer``, and close it."""
    if not isinstance(path, str):
        raise TypeError("path must be str")
    if not isinstance(size, int):
        raise TypeError("size must be int")
    if size < 0:
        raise ValueError("size must be >= 0")

    view = memoryview(buffer)
    if view.readonly:
        raise TypeError("buffer must be writable")
    if size > view.nbytes:
        raise ValueError("size cannot exceed buffer length")

    fd = os.open(path, os.O_RDONLY)
    try:
        data = os.read(fd, size)
    finally:
        os.close(fd)

    nread = len(data)
    view[:nread] = data
    return nread


__all__ = ["check_u32", "check_u8", "check_i8", "read_into"]
