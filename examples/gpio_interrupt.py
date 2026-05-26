"""Wait for a GPIO interrupt delivered as a signal (poll up to 10 s).

Like nuttx-apps ``examples/gpio/gpio_main.c`` wait mode (``-w``): configure the
pin as an interrupt, register a ``struct sigevent`` with ``GPIOC_REGISTER``, then
block until ``SIGUSR1`` is raised or the wait times out.

Usage::

    python gpio_interrupt.py [/dev/gpioN]

If no device path is given, ``/dev/gpio2`` is used. Install a handler for
``SIGUSR1``, then trigger the pin (button, jumper, or another GPIO) to see the
interrupt and read back the line level.

Before running, ensure ``CONFIG_DEV_GPIO`` is enabled and the board exposes the
chosen ``/dev/gpioN`` device.
"""

import argparse
import signal
import sys
import time

from nuttx_periphery import GPIO, GPIOPinType
from nuttx_periphery.sigevent import Sigevent

WAIT_SEC = 10


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "gpio",
        nargs="?",
        default="/dev/gpio2",
        help="GPIO device path (default: /dev/gpio2)",
    )
    return parser.parse_args()


def main(gpio_arg: str) -> int:
    """Configure *gpio_arg* as an interrupt and wait for ``SIGUSR1``."""
    received = False

    def on_interrupt(signum: int, frame) -> None:
        nonlocal received
        received = True
        print(f"Interrupt received: signum={signum}")

    signo = signal.SIGUSR1
    # Python level signal handler for SIGUSR1
    signal.signal(signo, on_interrupt)

    # NuttX signal handler for SIGUSR1
    notify = Sigevent.signal(signo)

    with GPIO(gpio_arg) as gpio:
        gpio.set_pin_type(GPIOPinType.GPIO_INTERRUPT_PIN)
        print(f"GPIO {gpio_arg} configured as interrupt, waiting up to {WAIT_SEC}s ...")

        gpio.register_signal(notify)

        deadline = time.time() + WAIT_SEC
        while not received and time.time() < deadline:
            time.sleep(1)

        gpio.unregister_signal()

        if received:
            print(f"Interrupt received, value={gpio.read()}")
        else:
            print(f"Timeout (no signal within {WAIT_SEC} seconds)")

    return 0


if __name__ == "__main__":
    args = parse_args()
    sys.exit(main(args.gpio))
