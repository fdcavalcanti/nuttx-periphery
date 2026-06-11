"""Wait for a oneshot timer expiration via a signal.

Register ``SIGUSR1`` as the NuttX oneshot notification, start the timer, then
poll once per second until the handler runs.

Usage::

    python oneshot.py [--timeout SEC] [/dev/oneshot]

If no device path is given, ``/dev/oneshot`` is used.
"""

import argparse
import signal
import sys
import time

from nuttx_periphery import OneshotTimer

DEFAULT_TIMEOUT_SEC = 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "oneshot",
        nargs="?",
        default="/dev/oneshot",
        help="Oneshot device path (default: /dev/oneshot)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SEC,
        metavar="SEC",
        help=f"Timer duration in seconds (default: {DEFAULT_TIMEOUT_SEC})",
    )
    return parser.parse_args()


def main(oneshot_arg: str, timeout_sec: float) -> int:
    """Start *oneshot_arg* with a signal notification and wait for expiration."""
    if timeout_sec <= 0:
        print("Error: --timeout must be > 0", file=sys.stderr)
        return 1

    timeout_us = int(timeout_sec * 1_000_000)
    expired = False

    def on_timer(signum: int, frame) -> None:
        nonlocal expired
        expired = True

    signo = signal.SIGUSR1
    signal.signal(signo, on_timer)

    with OneshotTimer(oneshot_arg) as oneshot:
        max_delay = oneshot.max_delay()
        print(
            f"Oneshot {oneshot_arg}: max delay "
            f"{max_delay.tv_sec}s + {max_delay.tv_nsec}ns"
        )

        oneshot.set_signo(signo)
        oneshot.set_timeout_us(timeout_us)
        print(f"Starting {timeout_sec}s timeout, waiting for SIGUSR1 ...")
        oneshot.start()

        while not expired:
            current = oneshot.current()
            print(f"Current time: {current.tv_sec}s + {current.tv_nsec}ns")
            time.sleep(1)

        print(f"Oneshot expired: {expired}")
        oneshot.cancel()

    print("Done")
    return 0


if __name__ == "__main__":
    args = parse_args()
    sys.exit(main(args.oneshot, args.timeout))
