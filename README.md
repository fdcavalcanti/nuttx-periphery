# nuttx-periphery

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![NuttX](https://img.shields.io/badge/platform-NuttX-lightgrey.svg)](https://nuttx.apache.org/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](#license)

**Pure Python peripheral APIs** for NuttX character devices.

`nuttx_periphery` wraps GPIO, PWM, User LED, and Timer character devices with typed Python methods built on `os.open`, `fcntl.ioctl`, and ctypes structures aligned with NuttX headers.

NuttX is a POSIX compliant real-time operating system (RTOS) which now has CPython support on QEMU RISC-V and Espressif devices such as ESP32-P4.

## Installation

On NuttX RTOS, this package is installed automatically during build of Python (see `INTERPRETERS_CPYTHON_INSTALL_NUTTX_PACKAGE` on `nuttx-apps`).

## Features

- **GPIO**: output, input, and signal-based interrupt registration.
- **User LED**: per-LED and mask read/write.
- **PWM**: per-channel frequency, duty, and optional dead-time / pulse count.
- **Timer**: status polling, timeouts, and signal notification.
- **Generic device access**: raw read/ioctl via `CharacterDevice`.

## Requirements

- NuttX running on microcontroller with CPython available
  - esp32p4-function-ev-board:python
- NuttX on QEMU
  - rv-virt:python

## Quick Start

Start Python on NuttX:

```console
NuttShell (NSH) NuttX-12.4.0
nsh> python
```

Toggle pin state using GPIO module:
```python
from nuttx_periphery import GPIO, GPIOPinType

with GPIO("/dev/gpio0") as gpio:
    gpio.set_pin_type(GPIOPinType.GPIO_OUTPUT_PIN)
    gpio.write(True)
```

Or operate a PWM pin:
```python
from nuttx_periphery.pwm import PWM

with PWM("/dev/pwm0", channel_count=1) as pwm:
  print(pwm.list_channels())  # See available channels
  pwm.frequency = 200
  pwm.channel[0].duty = 45
  pwm.apply()

  pwm.start()
  time.sleep(5)
  pwm.stop()
```

## Examples

Additional runnable scripts are in [`examples/`](examples/):

- [`gpio_out.py`](examples/gpio_out.py) — blink a GPIO output
- [`gpio_interrupt.py`](examples/gpio_interrupt.py) — wait for a GPIO interrupt via signal
- [`pwm.py`](examples/pwm.py) — read and write PWM channel settings
- [`timer.py`](examples/timer.py) — poll timer time left until expiration
- [`timer_notification.py`](examples/timer_notification.py) — wait for timer expiration via signal

Download scripts to the target board using wget:

- Host:

Clone this repository on the host machine and start Python HTTP server

```console
cd nuttx-periphery
python3 -m http.server
```

- Target:

Use wget on the target board to download scripts
```bash
wget -o /tmp/gpio_out.py http://192.168.0.20:8000/examples/gpio_out.py
python /tmp/gpio_out.py
```

## Contributing

Contributions are welcome.

- Tests are required for new features.
- Code linting via `pre-commit` is required.

Install from source:

```bash
git clone <repository-url>
cd nuttx-periphery
python -m pip install -e ".[dev]"
pre-commit install
pytest
```

The generated `.whl` and install script will be in `dist/`.

## License

This project is licensed under the Apache License 2.0.
