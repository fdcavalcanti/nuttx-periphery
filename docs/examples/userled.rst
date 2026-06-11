User LED
========

``examples/userled.py`` reads the supported LED bitmask, blinks each supported
LED for one second, then turns all LEDs off.

Usage:

.. code-block:: bash

   python userled.py [/dev/userleds]

Default device: ``/dev/userleds``.

.. literalinclude:: ../../examples/userled.py
   :language: python
   :caption: examples/userled.py
