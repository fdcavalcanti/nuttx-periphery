Oneshot timer
=============

Signal notification — wait for expiration
-----------------------------------------

``examples/oneshot.py`` registers ``SIGUSR1`` as the oneshot notification,
starts a configurable timeout, and polls ``current()`` once per second until
the handler runs.

Usage:

.. code-block:: bash

   python oneshot.py [--timeout SEC] [/dev/oneshot]

Default device: ``/dev/oneshot``. Default timeout: 2 seconds. Install a Python
handler with ``signal.signal`` before starting the timer.

.. literalinclude:: ../../examples/oneshot.py
   :language: python
   :caption: examples/oneshot.py
