"""Blink each supported user LED in sequence.

Open the user LED device, read the supported bitmask, turn each LED on for one
second, then turn all LEDs off.

Usage::

    python userled.py [/dev/userleds]

If no device path is given, ``/dev/userleds`` is used.
"""

import argparse
import sys
from time import sleep

from nuttx_periphery import UserLED

BLINK_SEC = 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "userled",
        nargs="?",
        default="/dev/userleds",
        help="User LED device path (default: /dev/userleds)",
    )
    return parser.parse_args()


def main(userled_arg: str) -> int:
    """Blink each supported LED on *userled_arg* once, then clear all."""
    with UserLED(userled_arg) as leds:
        supported = leds.supported()
        print(f"User LED {userled_arg}: supported mask {supported:#x}")
        print(f"Current state: {leds.get_all():#x}")

        for index in range(32):
            if not (supported & (1 << index)):
                continue

            print(f"LED {index} ON")
            leds.set_led(index, True)
            sleep(BLINK_SEC)
            leds.set_led(index, False)

        leds.set_all(0)
        print(f"All LEDs off, state={leds.get_all():#x}")
        print("Done")

    return 0


if __name__ == "__main__":
    args = parse_args()
    sys.exit(main(args.userled))
