Project overview
================

**nuttx_periphery** wraps GPIO, PWM, User LED, Timer, and Oneshot timer
character devices with typed Python methods built on ``os.open``,
``fcntl.ioctl``, and ctypes structures aligned with NuttX headers.

Online documentation: `Read the Docs <https://nuttx-periphery.readthedocs.io/en/stable/>`_

NuttX is a POSIX compliant real-time operating system (RTOS) which now has CPython
support on QEMU RISC-V and Espressif devices such as ESP32-P4.

Installation
------------

On NuttX RTOS, this package is installed automatically during build of Python
(see ``INTERPRETERS_CPYTHON_INSTALL_NUTTX_PACKAGE`` on ``nuttx-apps``).

Features
--------

- **GPIO**: output, input, and signal-based interrupt registration.
- **User LED**: per-LED and mask read/write.
- **PWM**: per-channel frequency, duty, and optional dead-time / pulse count.
- **Timer**: status polling, timeouts, and signal notification.
- **Oneshot timer**: start/cancel, current time, maximum delay, and signal
  notification via a single ``OSIOC_START`` call.
- **Generic device access**: raw read/ioctl via :class:`~nuttx_periphery.device.CharacterDevice`.

Requirements
------------

- NuttX running on microcontroller with CPython available

  - ``esp32p4-function-ev-board:python``
- NuttX on QEMU

  - ``rv-virt:python``

Quick start
-----------

Execute the following snippet from the Python interpreter on target:

.. code-block:: console

   NuttShell (NSH) NuttX-12.4.0
   nsh> python

.. code-block:: python

   from nuttx_periphery import GPIO, GPIOPinType

   with GPIO("/dev/gpio0") as gpio:
       gpio.set_pin_type(GPIOPinType.GPIO_OUTPUT_PIN)
       gpio.write(True)

Examples
--------

See :doc:`examples/index` for runnable examples of GPIO, PWM, Timer, Oneshot
timer, and User LED.

Contributing
------------

Contributions are welcome.

- Tests are required for new features.
- Code linting via ``pre-commit`` is required.

Install from source:

.. code-block:: bash

   git clone <repository-url>
   cd nuttx-periphery
   python -m pip install -e ".[dev]"
   pre-commit install
   pytest

The generated ``.whl`` and install script will be in ``dist/``.

License
-------

This project is licensed under the Apache License 2.0.
