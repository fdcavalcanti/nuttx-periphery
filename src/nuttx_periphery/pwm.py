"""PWM API for NuttX PWM character devices."""
import ctypes
import struct
from array import array
from dataclasses import dataclass

from .device import CharacterDevice
from .ioctl_consts import (
    PWMIOC_FAULTS_FETCH_AND_CLEAR,
    PWMIOC_GETCHARACTERISTICS,
    PWMIOC_SETCHARACTERISTICS,
    PWMIOC_START,
    PWMIOC_STOP,
)
from .utils import check_i8, check_u8, check_u32

POINTER_SIZE = ctypes.sizeof(ctypes.c_void_p)


@dataclass
class PWMChannel:
    """NuttX PWM channel structure.

    Attributes:
    - duty: Duty of the pulse train, "1"-to-"0" duration.
    - channel: Channel number.
    - cpol: Channel polarity.
    - dcpol: Disabled channel polarity.

    Requires CONFIG_PWM_DEADTIME:
    - dead_time_a: Dead time value for main output.
    - dead_time_b: Dead time value for complementary output.
    """

    duty: int
    channel: int
    cpol: int = 0
    dcpol: int = 0
    dead_time_a: int | None = None
    dead_time_b: int | None = None
    count: int | None = None

    def _pack_channel(self, *, has_deadtime: bool, has_pulsecount: bool) -> bytes:
        check_u32(self.duty, "channel.duty")
        check_u8(self.cpol, "channel.cpol")
        check_u8(self.dcpol, "channel.dcpol")
        check_i8(self.channel, "channel.channel")

        payload = bytearray(struct.pack("@I", self.duty))
        if has_deadtime:
            if self.dead_time_a is None or self.dead_time_b is None:
                raise ValueError(
                    "channel.dead_time_a and channel.dead_time_b must both be set "
                    "when has_deadtime=True"
                )
            check_u32(self.dead_time_a, "channel.dead_time_a")
            check_u32(self.dead_time_b, "channel.dead_time_b")
            payload.extend(struct.pack("@I", self.dead_time_a))
            payload.extend(struct.pack("@I", self.dead_time_b))
        payload.extend(struct.pack("@BBb", self.cpol, self.dcpol, self.channel))

        if has_pulsecount:
            if self.count is None:
                raise ValueError("channel.count must be set when has_pulsecount=True")
            check_u32(self.count, "channel.count")
            payload.extend(b"\x00" * ((-len(payload)) % 4))
            payload.extend(struct.pack("@I", self.count))

        payload.extend(b"\x00" * ((-len(payload)) % 4))
        return bytes(payload)


@dataclass
class PWMInfo:
    """
    NuttX PWM information structure.

    This dataclass represents the arguments passed to or returned from the NuttX
    PWM device for configuration and querying of PWM timing properties, output
    polarity, deadtime, and extra arguments. It is intended to serialize to and
    from the C structure expected by the underlying NuttX kernel driver.

    Attributes:
        frequency (int): Output frequency of the PWM signal, in Hertz.
        duty (int, optional): Duty cycle value for single channel mode.
        cpol (int, optional): Polarity for main output (0=normal, 1=inverted).
        dcpol (int, optional): Polarity for disabled channel output.
        arg (int, optional): Opaque field for board-specific arguments (used as
                             pointer or integer).

        Requires CONFIG_PWM_DEADTIME:
        dead_time_a (int | None, optional): Dead time for main output.
        dead_time_b (int | None, optional): Dead time for complementary output.

        Requires CONFIG_PWM_PULSECOUNT:
        count (int | None, optional): Pulse count.

        Requires CONFIG_PWM_NCHANNELS > 1:
        channels (list[PWMChannel] | None, optional): List of PWMChannel objects for
                                                      multi-channel operation.

    Methods:
        to_bytes(...): Serialize this structure to the binary format expected by the
                       kernel driver.
        from_bytes(...): Construct a PWMInfo from bytes returned by the driver.

    Typical usage:
        # For single channel
        info = PWMInfo(frequency=1000, duty=50)
        pwm.set_characteristics(info)

        # For multi-channel
        info = PWMInfo(
            frequency=1000,
            channels=[
                PWMChannel(duty=100),
                PWMChannel(duty=50),
            ],
        )
        pwm = PWM("/dev/pwm0", channel_count=2)
        pwm.set_characteristics(info)
    """

    frequency: int
    duty: int = 0
    cpol: int = 0
    dcpol: int = 0
    arg: int = 0
    dead_time_a: int | None = None
    dead_time_b: int | None = None
    count: int | None = None
    channels: list[PWMChannel] | None = None

    def to_bytes(
        self,
        *,
        channel_count: int | None = None,
        has_deadtime: bool = False,
        has_pulsecount: bool = False,
    ) -> bytes:
        check_u32(self.frequency, "frequency")
        if self.arg < 0:
            raise ValueError("arg must be >= 0")

        payload = bytearray(struct.pack("@I", self.frequency))

        # New NuttX layout always uses channels[] with CONFIG_PWM_NCHANNELS.
        if self.channels is None:
            channels = [
                PWMChannel(
                    duty=self.duty,
                    cpol=self.cpol,
                    dcpol=self.dcpol,
                    channel=0,
                    dead_time_a=self.dead_time_a,
                    dead_time_b=self.dead_time_b,
                    count=self.count,
                )
            ]
        else:
            channels = self.channels

        if channel_count is None:
            channel_count = len(channels)
        if channel_count <= 0:
            raise ValueError("channel_count must be > 0")
        if len(channels) != channel_count:
            raise ValueError("len(channels) must match channel_count")

        for idx, channel in enumerate(channels):
            if not isinstance(channel, PWMChannel):
                raise TypeError(f"channels[{idx}] must be PWMChannel")
            payload.extend(
                channel._pack_channel(
                    has_deadtime=has_deadtime,
                    has_pulsecount=has_pulsecount,
                )
            )

        payload.extend(b"\x00" * ((-len(payload)) % POINTER_SIZE))
        if POINTER_SIZE == 4:
            check_u32(self.arg, "arg")
            payload.extend(struct.pack("@I", self.arg))
        else:
            if self.arg > 0xFFFFFFFFFFFFFFFF:
                raise ValueError("arg is out of range for 64-bit pointer")
            payload.extend(struct.pack("@Q", self.arg))
        return bytes(payload)

    @classmethod
    def from_bytes(
        cls,
        data: bytes | bytearray | memoryview,
        *,
        channel_count: int | None = None,
        has_deadtime: bool = False,
        has_pulsecount: bool = False,
    ) -> "PWMInfo":
        if not isinstance(data, (bytes, bytearray, memoryview)):
            raise TypeError("data must be bytes, bytearray, or memoryview")

        buf = bytes(data)
        _require_len(
            buf, 4 + POINTER_SIZE, "data buffer too small for pwm_info_s header"
        )

        off = 0
        frequency = struct.unpack_from("@I", buf, off)[0]
        off += 4

        if channel_count is None or channel_count <= 0:
            channel_count = 1

        channels: list[PWMChannel] = []
        for _ in range(channel_count):
            channel, off = _unpack_channel(
                buf,
                off,
                has_deadtime=has_deadtime,
                has_pulsecount=has_pulsecount,
            )
            channels.append(channel)
        off += (-off) % POINTER_SIZE
        _require_len(
            buf, off + POINTER_SIZE, "data buffer too small for pwm_info_s.arg"
        )
        arg = struct.unpack_from("@I" if POINTER_SIZE == 4 else "@Q", buf, off)[0]

        channel0 = channels[0]
        return cls(
            frequency=frequency,
            duty=channel0.duty,
            cpol=channel0.cpol,
            dcpol=channel0.dcpol,
            arg=arg,
            dead_time_a=channel0.dead_time_a,
            dead_time_b=channel0.dead_time_b,
            count=channel0.count,
            channels=channels,
        )


class PWM(CharacterDevice):
    def __init__(
        self,
        path: str,
        nonblock: bool = False,
        *,
        channel_count: int | None = None,
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

        self.channel_count = 1 if channel_count is None else channel_count
        self.has_deadtime = has_deadtime
        self.has_pulsecount = has_pulsecount
        super().__init__(path=path, nonblock=nonblock)

    def new_pwm_info(
        self,
        *,
        frequency: int,
        duty: int = 0,
        cpol: int = 0,
        dcpol: int = 0,
        arg: int = 0,
        dead_time_a: int | None = None,
        dead_time_b: int | None = None,
        count: int | None = None,
        channels: list[PWMChannel] | None = None,
    ) -> PWMInfo:
        """Create a ``PWMInfo`` pre-filled from this PWM configuration."""
        if channels is None:
            if self.channel_count > 1:
                channels = [
                    PWMChannel(duty=0, channel=index + 1)
                    for index in range(self.channel_count)
                ]
            else:
                if self.has_deadtime:
                    if dead_time_a is None:
                        dead_time_a = 0
                    if dead_time_b is None:
                        dead_time_b = 0
                if self.has_pulsecount and count is None:
                    count = 0
                channels = [
                    PWMChannel(
                        duty=duty,
                        channel=0,
                        cpol=cpol,
                        dcpol=dcpol,
                        dead_time_a=dead_time_a,
                        dead_time_b=dead_time_b,
                        count=count,
                    )
                ]

        if len(channels) != self.channel_count:
            raise ValueError("len(channels) must match PWM.channel_count")

        return PWMInfo(
            frequency=frequency,
            duty=duty,
            cpol=cpol,
            dcpol=dcpol,
            arg=arg,
            dead_time_a=dead_time_a,
            dead_time_b=dead_time_b,
            count=count,
            channels=channels,
        )

    def set_characteristics(
        self,
        data: bytes | bytearray | memoryview | PWMInfo,
    ) -> None:
        if isinstance(data, PWMInfo):
            data = data.to_bytes(
                channel_count=self.channel_count,
                has_deadtime=self.has_deadtime,
                has_pulsecount=self.has_pulsecount,
            )
        elif not isinstance(data, (bytes, bytearray, memoryview)):
            raise TypeError("data must be PWMInfo, bytes, bytearray, or memoryview")
        self.ioctl(PWMIOC_SETCHARACTERISTICS, data)

    def _get_charateristics(self, size: int) -> bytes:
        """Low-level raw read of packed ``pwm_info_s`` bytes."""
        if not isinstance(size, int):
            raise TypeError("size must be int")
        if size <= 0:
            raise ValueError("size must be > 0")
        buf = bytearray(size)
        self.ioctl(PWMIOC_GETCHARACTERISTICS, buf)
        return bytes(buf)

    def get_characteristics(
        self,
        size: int | None = None,
    ) -> PWMInfo:
        """High-level read of characteristics as a ``PWMInfo`` object."""
        if size is None:
            size = _pwm_info_size(
                channel_count=self.channel_count,
                has_deadtime=self.has_deadtime,
                has_pulsecount=self.has_pulsecount,
            )

        data = self._get_charateristics(size)
        return PWMInfo.from_bytes(
            data,
            channel_count=self.channel_count,
            has_deadtime=self.has_deadtime,
            has_pulsecount=self.has_pulsecount,
        )

    def start(self) -> None:
        self.ioctl(PWMIOC_START, 0)

    def stop(self) -> None:
        self.ioctl(PWMIOC_STOP, 0)

    def faults_fetch_and_clear(self, mask: int | None = None) -> int | None:
        if mask is None:
            self.ioctl(PWMIOC_FAULTS_FETCH_AND_CLEAR, 0)
            return None
        if not isinstance(mask, int):
            raise TypeError("mask must be int or None")
        if mask < 0:
            raise ValueError("mask must be >= 0")
        faults = array("L", [mask])
        self.ioctl(PWMIOC_FAULTS_FETCH_AND_CLEAR, faults)
        return int(faults[0])


def _require_len(buf: bytes, needed: int, msg: str) -> None:
    if len(buf) < needed:
        raise ValueError(msg)


def _pack_channel(channel: PWMChannel, *, has_deadtime: bool) -> bytes:
    return channel._pack_channel(has_deadtime=has_deadtime, has_pulsecount=False)


def _unpack_channel(
    buf: bytes,
    off: int,
    *,
    has_deadtime: bool,
    has_pulsecount: bool,
) -> tuple[PWMChannel, int]:
    _require_len(buf, off + 4, "data buffer too small for channel duty")
    duty = struct.unpack_from("@I", buf, off)[0]
    off += 4

    dead_time_a = None
    dead_time_b = None
    if has_deadtime:
        _require_len(buf, off + 8, "data buffer too small for channel deadtime")
        dead_time_a = struct.unpack_from("@I", buf, off)[0]
        off += 4
        dead_time_b = struct.unpack_from("@I", buf, off)[0]
        off += 4

    _require_len(buf, off + 3, "data buffer too small for channel polarity/index")
    cpol, dcpol, channel = struct.unpack_from("@BBb", buf, off)
    off += 3
    count = None
    if has_pulsecount:
        off += (-off) % 4
        _require_len(buf, off + 4, "data buffer too small for channel pulse count")
        count = struct.unpack_from("@I", buf, off)[0]
        off += 4

    off += (-off) % 4

    return (
        PWMChannel(
            duty=duty,
            channel=channel,
            cpol=cpol,
            dcpol=dcpol,
            dead_time_a=dead_time_a,
            dead_time_b=dead_time_b,
            count=count,
        ),
        off,
    )


def _pwm_info_size(
    *,
    channel_count: int | None,
    has_deadtime: bool,
    has_pulsecount: bool,
) -> int:
    size = 4  # frequency

    if channel_count is None or channel_count <= 0:
        channel_count = 1

    chan_size = 4  # duty
    if has_deadtime:
        chan_size += 8
    chan_size += 3  # cpol + dcpol + channel
    if has_pulsecount:
        chan_size += (-chan_size) % 4
        chan_size += 4  # count
    chan_size += (-chan_size) % 4
    size += chan_size * channel_count

    size += (-size) % POINTER_SIZE
    size += POINTER_SIZE  # arg pointer
    return size


__all__ = ["PWM", "PWMInfo", "PWMChannel"]
