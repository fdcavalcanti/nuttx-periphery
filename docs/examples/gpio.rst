GPIO
====

Output — blink an LED
---------------------

``examples/gpio_out.py`` configures a GPIO as output and toggles it five times
(on/off, 1 s each).

Usage:

.. code-block:: bash

   python gpio_out.py [/dev/gpioN]

Default device: ``/dev/gpio1``.

.. literalinclude:: ../../examples/gpio_out.py
   :language: python
   :caption: examples/gpio_out.py

Interrupt — wait for a signal
-----------------------------

``examples/gpio_interrupt.py`` configures a pin as an interrupt, registers a
``struct sigevent`` with ``GPIOC_REGISTER``, and waits up to 10 s for
``SIGUSR1``.

Usage:

.. code-block:: bash

   python gpio_interrupt.py [/dev/gpioN]

Default device: ``/dev/gpio2``. Install a handler for ``SIGUSR1``, then trigger
the pin (button, jumper, or another GPIO).

Ensure ``CONFIG_DEV_GPIO`` is enabled and the board exposes the chosen
``/dev/gpioN`` device.

.. literalinclude:: ../../examples/gpio_interrupt.py
   :language: python
   :caption: examples/gpio_interrupt.py
