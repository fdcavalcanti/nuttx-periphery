"""nuttx_periphery package."""

import ctypes

_pointer_size = ctypes.sizeof(ctypes.c_void_p)
if _pointer_size not in (4, 8):
    raise RuntimeError("Unsupported pointer size")

from .gpio import GPIO, GPIOPinType
from .pwm import PWM, PWMChannel, PWMInfo
from .userled import UserLED
from device import CharacterDevice

__all__ = [
    "GPIO",
    "GPIOPinType",
    "UserLED",
    "PWM",
    "PWMInfo",
    "PWMChannel",
    "CharacterDevice",
]
