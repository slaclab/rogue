.. _protocols_rssi_client:

====================
RSSI Protocol Client
====================

``rogue::protocols::rssi::Client`` is a convenience wrapper for endpoint logic
initiating/maintaining RSSI links in client role.

It constructs and wires:

* ``Transport`` (lower/link side),
* ``Application`` (upper/payload side),
* ``Controller`` (state machine and reliability logic).

Use ``transport()`` to connect to the underlying link and ``application()`` to
connect upper-layer protocol blocks.

Example (Python):

.. code-block:: python

   import rogue.protocols.udp
   import rogue.protocols.rssi

   udp = rogue.protocols.udp.Client("127.0.0.1", 8200, True)
   rssi = rogue.protocols.rssi.Client(udp.maxPayload() - 8)

   # Link-layer stream connection
   udp == rssi.transport()

   # Start controller state machine
   rssi._start()

