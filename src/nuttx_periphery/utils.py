"""Shared utility helpers for nuttx_periphery."""

from __future__ import annotations


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


__all__ = ["check_u32", "check_u8", "check_i8"]
