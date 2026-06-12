"""PWM API for NuttX PWM character devices.

Wraps the PWM driver ioctls from ``include/nuttx/timers/pwm.h``:

- start / stop
- characteristics (``struct pwm_info_s`` / ``struct pwm_chan_s``)
- fault fetch and clear

Typical use::

    pwm = PWM("/dev/pwm0", channel_count=2, has_deadtime=True)
    pwm.frequency = 20_000
    pwm.channel[0].duty = 50          # percent (0–100)
    pwm.channel[1].duty = 75
    pwm.apply()                       # push settings to the driver
    pwm.start()
    pwm.stop()

``channel_count``, ``has_deadtime``, and ``has_pulsecount`` must match the
NuttX board configuration (``CONFIG_PWM_NCHANNELS``, ``CONFIG_PWM_DEADTIME``,
``CONFIG_PWM_PULSECOUNT``). Duty is stored in the driver as ``ub16_t``
(0–65535); this module exposes it as a percentage for convenience.

Changes to ``frequency`` or channel fields are held locally until
:meth:`PWM.apply` is called. Call :meth:`PWM.refresh` to reload from the driver
without writing.
"""

from __future__ import annotations

import ctypes
from dataclasses import dataclass

from .device import CharacterDevice
from .ioctl_consts import (
    PWMIOC_FAULTS_FETCH_AND_CLEAR,
    PWMIOC_GETCHARACTERISTICS,
    PWMIOC_SETCHARACTERISTICS,
    PWMIOC_START,
    PWMIOC_STOP,
)


def _PWMChannelStruct(has_deadtime=False, has_pulsecount=False):
    """Build a ``struct pwm_chan_s`` ctypes type for the given Kconfig layout."""
    f = [("duty", ctypes.c_uint32)]
    if has_deadtime:
        f += [("dead_time_a", ctypes.c_uint32), ("dead_time_b", ctypes.c_uint32)]
    f += [
        ("cpol", ctypes.c_uint8),
        ("dcpol", ctypes.c_uint8),
        ("channel", ctypes.c_int8),
    ]
    if has_pulsecount:
        f.append(("count", ctypes.c_uint32))
    return type("PWMChannelStruct", (ctypes.Structure,), {"_fields_": f})


def _PWMInfoStruct(channels, has_deadtime=False, has_pulsecount=False):
    """Build a ``struct pwm_info_s`` ctypes type with ``channels[N]``."""
    c = _PWMChannelStruct(has_deadtime, has_pulsecount)
    return type(
        "PWMInfoStruct",
        (ctypes.Structure,),
        {
            "_fields_": [
                ("frequency", ctypes.c_uint32),
                ("channels", c * channels),
                ("arg", ctypes.c_void_p),
            ]
        },
    )


def PWMInfoStruct(channels, has_deadtime=False, has_pulsecount=False):
    """Allocate a zeroed ``struct pwm_info_s`` for *channels* outputs."""
    return _PWMInfoStruct(channels, has_deadtime, has_pulsecount)()


@dataclass
class PWMChannel:
    """High-level view of one ``struct pwm_chan_s`` entry.

    ``channel`` is the NuttX channel index (``int8``). ``cpol`` and ``dcpol``
    are channel and disabled-channel polarity. ``dead_time_a`` and
    ``dead_time_b`` apply when ``has_deadtime=True``. ``count`` is the pulse
    count when ``has_pulsecount=True`` (0 = indefinite).

    ``duty`` is exposed as a percentage (0–100) and converted to ``ub16_t``
    (0–65535) for the driver.
    """

    _duty: int = 32767
    channel: int = 0
    cpol: int = 0
    dcpol: int = 0
    dead_time_a: int | None = None
    dead_time_b: int | None = None
    count: int | None = None

    MAX_DUTY = 65535
    MAX_DUTY_PERCENT = 100

    def from_ctypes(self, ctypes_struct: ctypes.Structure) -> PWMChannel:
        """Load fields from a native ``pwm_chan_s`` buffer element."""
        self._duty = ctypes_struct.duty
        self.channel = ctypes_struct.channel
        self.cpol = ctypes_struct.cpol
        self.dcpol = ctypes_struct.dcpol
        if hasattr(ctypes_struct, "dead_time_a"):
            self.dead_time_a = ctypes_struct.dead_time_a
        if hasattr(ctypes_struct, "dead_time_b"):
            self.dead_time_b = ctypes_struct.dead_time_b
        if hasattr(ctypes_struct, "count"):
            self.count = ctypes_struct.count
        return self

    def update_ctypes(self, ctypes_struct: ctypes.Structure) -> None:
        """Write this channel into a native ``pwm_chan_s`` buffer element."""
        if not isinstance(ctypes_struct, ctypes.Structure):
            raise TypeError("ctypes_struct must be ctypes.Structure")
        ctypes_struct.duty = self._duty
        ctypes_struct.channel = self.channel
        ctypes_struct.cpol = self.cpol
        ctypes_struct.dcpol = self.dcpol
        if hasattr(ctypes_struct, "dead_time_a") and self.dead_time_a is not None:
            ctypes_struct.dead_time_a = self.dead_time_a
        if hasattr(ctypes_struct, "dead_time_b") and self.dead_time_b is not None:
            ctypes_struct.dead_time_b = self.dead_time_b
        if hasattr(ctypes_struct, "count") and self.count is not None:
            ctypes_struct.count = self.count

    @property
    def duty(self) -> float:
        """Duty cycle in percent (0–100)."""
        return round(self._duty * self.MAX_DUTY_PERCENT / self.MAX_DUTY, 2)

    @duty.setter
    def duty(self, duty: int | float) -> None:
        if not isinstance(duty, int | float):
            raise TypeError("duty must be int or float")
        if duty < 0 or duty > self.MAX_DUTY_PERCENT:
            raise ValueError("duty must be between 0 and 100")
        self._duty = int(duty * self.MAX_DUTY / self.MAX_DUTY_PERCENT)


class PWM(CharacterDevice):
    """NuttX PWM character device (``/dev/pwm*``).

    Args:
        path: Device node path (e.g. ``"/dev/pwm0"``).
        inital_frequency: Default frequency (Hz) before the first driver read.
        channel_count: Number of channels (``CONFIG_PWM_NCHANNELS``).
        has_deadtime: Include dead-time fields (``CONFIG_PWM_DEADTIME``).
        has_pulsecount: Include pulse-count fields (``CONFIG_PWM_PULSECOUNT``).

    On construction the device is opened and current characteristics are read
    from the driver via ``PWMIOC_GETCHARACTERISTICS``.
    """

    def __init__(
        self,
        path: str,
        inital_frequency: int = 20,
        *,
        channel_count: int = 1,
        has_deadtime: bool = False,
        has_pulsecount: bool = False,
    ) -> None:
        if channel_count is not None and not isinstance(channel_count, int):
            raise TypeError("channel_count must be int or None")
        if channel_count is not None and channel_count <= 0:
            raise ValueError("channel_count must be > 0")
        if not isinstance(has_deadtime, bool):
            raise TypeError("has_deadtime must be bool")
        if not isinstance(has_pulsecount, bool):
            raise TypeError("has_pulsecount must be bool")

        self.channel_count = channel_count
        self.has_deadtime = has_deadtime
        self.has_pulsecount = has_pulsecount
        self._frequency = inital_frequency

        self._info_type = _PWMInfoStruct(
            self.channel_count, has_deadtime, has_pulsecount
        )
        self.pwm_info_size = ctypes.sizeof(self._info_type)
        self._info_t = self._info_type()
        self._channels = [PWMChannel() for _ in range(channel_count)]

        super().__init__(path=path)
        self._get_characteristics()

    def start(self) -> None:
        """Start PWM output (``PWMIOC_START``)."""
        self.ioctl(PWMIOC_START, 0)

    def stop(self) -> None:
        """Stop PWM output (``PWMIOC_STOP``)."""
        self.ioctl(PWMIOC_STOP, 0)

    @property
    def frequency(self) -> int:
        """PWM frequency in Hz."""
        return self._frequency

    @frequency.setter
    def frequency(self, freq: int) -> None:
        if not isinstance(freq, int):
            raise TypeError("frequency must be int")
        if freq <= 0:
            raise ValueError("frequency must be > 0")
        self._frequency = freq

    @property
    def channel(self) -> list[PWMChannel]:
        """Per-channel settings (index with ``pwm.channel[i]``)."""
        return self._channels

    def refresh(self) -> None:
        """Read characteristics from the driver (``PWMIOC_GETCHARACTERISTICS``)."""
        self._get_characteristics()

    def apply(self) -> None:
        """Write local settings to the driver and read them back."""
        self._set_characteristics()

    def list_channels(self) -> str:
        """Return a short summary of configured channel count."""
        return f"Channels available: {self.channel_count}"

    def fetch_and_clear_faults(self) -> None:
        """Fetch and clear driver faults (``PWMIOC_FAULTS_FETCH_AND_CLEAR``)."""
        self.ioctl(PWMIOC_FAULTS_FETCH_AND_CLEAR, 0)

    def _get_characteristics(self) -> ctypes.Structure:
        buf = bytearray(self.pwm_info_size)
        self.ioctl(PWMIOC_GETCHARACTERISTICS, buf)
        self._info_t = self._info_type.from_buffer_copy(buf)
        for index, ctypes_ch in enumerate(self._info_t.channels):
            self._channels[index].from_ctypes(ctypes_ch)
        self._frequency = self._info_t.frequency
        return self._info_t

    def _set_characteristics(self, pwm_info: ctypes.Structure | None = None) -> None:
        for index, channel in enumerate(self._channels):
            channel.update_ctypes(self._info_t.channels[index])
        self._info_t.frequency = self._frequency

        if pwm_info is None:
            pwm_info = self._info_t
        if not isinstance(pwm_info, ctypes.Structure):
            raise TypeError("pwm_info must be ctypes.Structure")

        self.ioctl(PWMIOC_SETCHARACTERISTICS, bytes(pwm_info))
        self._get_characteristics()


__all__ = ["PWM", "PWMChannel", "PWMInfoStruct", "_PWMInfoStruct"]
