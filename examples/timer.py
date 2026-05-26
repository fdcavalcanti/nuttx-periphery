"""Run a NuttX timer for 10 seconds, printing time left each second.

Open a timer device, set a 10 s timeout, start it, poll ``timeleft`` once per
second until the period elapses, then stop and close.

Usage::

    python timer.py [/dev/timerN]

If no device path is given, ``/dev/timer0`` is used.
"""

import argparse
import sys
from time import sleep

from nuttx_periphery import Timer

TIMEOUT_SEC = 10
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
    """Set a 10 s timeout on *timer_arg*, poll timeleft each second, then stop."""
    with Timer(timer_arg) as tmr:
        tmr.set_timeout_us(TIMEOUT_US)
        print(f"Timer {timer_arg}: {TIMEOUT_SEC}s timeout set")
        tmr.start()

        for _ in range(TIMEOUT_SEC):
            status = tmr.get_status_us()
            print(
                f"Flags: {status.flags}, Timeout: {status.timeout}, "
                f"Time left: {status.timeleft}"
            )
            sleep(1)

        tmr.stop()
        print("Done")

    return 0


if __name__ == "__main__":
    args = parse_args()
    sys.exit(main(args.timer))
