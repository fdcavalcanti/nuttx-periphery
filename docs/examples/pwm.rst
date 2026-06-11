PWM
===

``examples/pwm.py`` reads and writes per-channel PWM settings: set frequency
and duty, push them to the driver with :meth:`~nuttx_periphery.pwm.PWM.apply`,
then start output for five seconds.

Usage:

.. code-block:: bash

   python pwm.py [/dev/pwmN] [-c CHANNELS]

Defaults: device ``/dev/pwm0``, one channel.

Match ``--channels`` and board Kconfig (``CONFIG_PWM_NCHANNELS``,
``CONFIG_PWM_DEADTIME``, ``CONFIG_PWM_PULSECOUNT``) when constructing
:class:`~nuttx_periphery.pwm.PWM`.

.. literalinclude:: ../../examples/pwm.py
   :language: python
   :caption: examples/pwm.py
