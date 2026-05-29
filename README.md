# nuttx-periphery

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![NuttX](https://img.shields.io/badge/platform-NuttX-lightgrey.svg)](https://nuttx.apache.org/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](#license)

**Pure Python peripheral APIs** for NuttX character devices.

`nuttx_periphery` wraps GPIO, PWM, User LED, and Timer character devices with typed Python methods built on `os.open`, `fcntl.ioctl`, and ctypes structures aligned with NuttX headers.

NuttX is a POSIX compliant real-time operating system (RTOS) which now has CPython support on QEMU RISC-V and Espressif devices such as ESP32-P4.

## Installation

Currently pip installations are very slow due to the amount of imports required. To fix this, a custom installation script is provided.

> **NOTE:**
> This process will be simplified when PyPi releases are available.

On the host machine, clone this repository, generate the .whl file and start a http server:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -e .
python3 -m build --wheel
python3 -m http.server
```

On the target, download the install script and wheel to `/tmp/`:
```bash
wget -O /tmp/install-packages.py <host IP>:8000/scripts/install-packages.py
wget -O /tmp/nuttx_periphery-0.1.0-py3-none-any.whl <host IP>:8000/dist/nuttx_periphery-0.1.0-py3-none-any.whl
```

Now run the installer (defaults: install to `/data`, use the newest `.whl` in the script directory):

```bash
python /tmp/install-packages.py /data /tmp/nuttx_periphery-0.1.0-py3-none-any.whl
export PYTHONPATH=/data:$PYTHONPATH
```

The script and wheel must live in the same directory (e.g. `/tmp/`) unless the wheel path is passed explicitly.

## Features

- **GPIO**: output, input, and signal-based interrupt registration.
- **User LED**: per-LED and mask read/write.
- **PWM**: per-channel frequency, duty, and optional dead-time / pulse count.
- **Timer**: status polling, timeouts, and signal notification.
- **Generic device access**: raw read/ioctl via `CharacterDevice`.

## Requirements

- NuttX running on microcontroller with CPython available
  - esp32p4-function-ev-board:python
- NuttX on QEMU (rv-virt:python)
  - rv-virt:python

## Quick Start

Execute the following snippet from the Python interpreter on target:

```python
from nuttx_periphery import GPIO, GPIOPinType

with GPIO("/dev/gpio0") as gpio:
    gpio.set_pin_type(GPIOPinType.GPIO_OUTPUT_PIN)
    gpio.write(True)
```

## Examples

Additional runnable scripts are in [`examples/`](examples/):

- [`gpio_out.py`](examples/gpio_out.py) — blink a GPIO output
- [`gpio_interrupt.py`](examples/gpio_interrupt.py) — wait for a GPIO interrupt via signal
- [`pwm.py`](examples/pwm.py) — read and write PWM channel settings
- [`timer.py`](examples/timer.py) — poll timer time left until expiration
- [`timer_notification.py`](examples/timer_notification.py) — wait for timer expiration via signal

Run on a NuttX board:

```bash
wget -O /tmp/gpio_out.py <host IP>:8000/examples/gpio_out.py
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
