.. _protocols_rssi_server:

====================
RSSI Protocol Server
====================

``rogue::protocols::rssi::Server`` is the convenience wrapper for endpoint
logic running RSSI in server role.

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

   udp = rogue.protocols.udp.Server(0, True)
   rssi = rogue.protocols.rssi.Server(udp.maxPayload() - 8)

   # Link-layer stream connection
   udp == rssi.transport()

   # Start controller state machine
   rssi._start()
