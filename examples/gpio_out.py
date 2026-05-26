"""Drive a GPIO as output and blink five times (on/off, 1 s each).

Like nuttx-apps ``examples/gpio/gpio_main.c`` output mode: open the device,
set ``GPIO_OUTPUT_PIN``, then toggle the line with ``GPIOC_WRITE``.

Usage::

    python gpio_out.py [/dev/gpioN]

If no device path is given, ``/dev/gpio1`` is used. Wire an LED (or scope) to
that pin on your board; the script prints each transition and exits when done.
"""

import argparse
import sys
from time import sleep

from nuttx_periphery import GPIO, GPIOPinType


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "gpio",
        nargs="?",
        default="/dev/gpio1",
        help="GPIO device path (default: /dev/gpio1)",
    )
    return parser.parse_args()


def main(gpio_arg: str) -> int:
    """Configure *gpio_arg* as output and toggle it high/low five times."""
    gpio = GPIO(gpio_arg)
    gpio.set_pin_type(GPIOPinType.GPIO_OUTPUT_PIN)
    print(f"GPIO {gpio_arg} set to output")

    for _ in range(5):
        print("Led ON")
        gpio.write(True)
        sleep(1)
        print("Led OFF")
        gpio.write(False)
        sleep(1)

    print("Done")
    return 0


if __name__ == "__main__":
    args = parse_args()
    sys.exit(main(args.gpio))
