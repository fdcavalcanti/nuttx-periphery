"""nuttx_periphery package."""

import ctypes

from .device import CharacterDevice
from .gpio import GPIO, GPIOPinType
from .pwm import PWM
from .timer import Timer, TimerStatus
from .userled import UserLED

_pointer_size = ctypes.sizeof(ctypes.c_void_p)
if _pointer_size not in (4, 8):
    raise RuntimeError("Unsupported pointer size")


__all__ = [
    "GPIO",
    "GPIOPinType",
    "UserLED",
    "PWM",
    "Timer",
    "TimerStatus",
    "CharacterDevice",
]
