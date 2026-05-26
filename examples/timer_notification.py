"""Wait for a timer expiration via a signal (5 s timeout).

Register ``SIGUSR1`` as the NuttX timer notification, start the timer, then
poll status once per second until the handler runs (or the timer stops).

Usage::

    python timer_notification.py [/dev/timerN]

If no device path is given, ``/dev/timer0`` is used.
"""

import argparse
import signal
import sys
import time

from nuttx_periphery import Timer

TIMEOUT_SEC = 5
TIMEOUT_US = TIMEOUT_SEC * 1_000_000


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "timer",
        nargs="?",
        default="/dev/timer0",
        help="Timer device path (default: /dev/timer0)",
    )
    return parser.parse_args()


def main(timer_arg: str) -> int:
    """Start *timer_arg* with a signal notification and wait for expiration."""
    expired = False

    def on_timer(signum: int, frame) -> None:
        nonlocal expired
        expired = True  # keep minimal; no I/O, no locks

    signo = signal.SIGUSR1
    # Python level signal handler for SIGUSR1
    signal.signal(signo, on_timer)

    with Timer(timer_arg) as tmr:
        tmr.set_notification(signo, periodic=False)
        tmr.set_timeout_us(TIMEOUT_US)
        print(f"Timer {timer_arg}: {TIMEOUT_SEC}s timeout set, waiting for SIGUSR1 ...")
        tmr.start()

        # NuttX CPython has no signal.pause(); wait in a sleep loop instead.
        while not expired and tmr.is_active():
            status = tmr.get_status_us()
            print(f"Time left: {status.timeleft}")
            time.sleep(1)

        print(f"Timer expired: {expired}")
        tmr.stop()

    print("Done")
    return 0


if __name__ == "__main__":
    args = parse_args()
    sys.exit(main(args.timer))
