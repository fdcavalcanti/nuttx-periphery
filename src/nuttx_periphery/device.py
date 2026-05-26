"""Shared character-device helpers for NuttX peripheral classes."""

from __future__ import annotations

import fcntl
import os
from typing import Optional, Union

IoctlArg = Union[int, bytes, bytearray, memoryview, None]


class CharacterDevice:
    """Minimal wrapper around a character device file descriptor."""

    def __init__(self, path: str, nonblock: bool = False) -> None:
        if not isinstance(path, str):
            raise TypeError("path must be str")
        if not isinstance(nonblock, bool):
            raise TypeError("nonblock must be bool")

        self._path = path
        self._fd: Optional[int] = None
        self.open(nonblock=nonblock)

    def __enter__(self) -> "CharacterDevice":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    @property
    def path(self) -> str:
        return self._path

    def open(self, nonblock: bool = False) -> None:
        """Open the device if it is not open yet."""
        if self._fd is not None:
            return

        flags = os.O_RDWR
        if nonblock:
            flags |= os.O_NONBLOCK

        self._fd = os.open(self._path, flags)

    def close(self) -> None:
        """Close the device if it is open."""
        if self._fd is None:
            return

        fd = self._fd
        self._fd = None
        os.close(fd)

    def fileno(self) -> int:
        """Return the underlying file descriptor."""
        if self._fd is None:
            raise ValueError("device is closed")
        return self._fd

    def read(self, buffer: bytearray | memoryview, size: int) -> int:
        """Read up to ``size`` bytes into ``buffer`` from this device."""
        if not isinstance(size, int):
            raise TypeError("size must be int")
        if size < 0:
            raise ValueError("size must be >= 0")

        view = memoryview(buffer)
        if view.readonly:
            raise TypeError("buffer must be writable")
        if size > view.nbytes:
            raise ValueError("size cannot exceed buffer length")

        data = os.read(self.fileno(), size)
        nread = len(data)
        view[:nread] = data
        return nread

    def ioctl(self, cmd: int, arg: IoctlArg = None) -> int:
        """Issue an ioctl on the device descriptor.

        Returns the NuttX driver ioctl handler result (``0`` on success,
        negative ``errno`` on failure).
        """
        if not isinstance(cmd, int):
            raise TypeError("cmd must be int")

        fd = self.fileno()

        if arg is None:
            return int(fcntl.ioctl(fd, cmd))

        # Mutable buffers must use the default mutate_flag so fcntl returns the
        # driver status (int). With mutate_flag=False, NuttX Python returns the
        # buffer contents as bytes and int() would fail.
        result = fcntl.ioctl(fd, cmd, arg)
        return result
