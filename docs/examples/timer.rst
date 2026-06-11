Timer
=====

Poll status — time left until expiration
----------------------------------------

``examples/timer.py`` sets a 10 s timeout, starts the timer, prints
``timeleft`` once per second, then stops.

Usage:

.. code-block:: bash

   python timer.py [/dev/timerN]

Default device: ``/dev/timer0``.

.. literalinclude:: ../../examples/timer.py
   :language: python
   :caption: examples/timer.py

Signal notification — wait for expiration
-----------------------------------------

``examples/timer_notification.py`` registers ``SIGUSR1`` as the timer
notification, starts a 5 s timeout, and polls until the handler runs.

Usage:

.. code-block:: bash

   python timer_notification.py [/dev/timerN]

Default device: ``/dev/timer0``. Install a Python handler with
``signal.signal`` before starting the timer.

.. literalinclude:: ../../examples/timer_notification.py
   :language: python
   :caption: examples/timer_notification.py
