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

Code-backed behavior notes
==========================

- ``Client`` is a thin bundle around ``Transport``, ``Application``, and a
  client-role ``Controller`` created in ``src/rogue/protocols/rssi/Client.cpp``.
- Python bindings expose ``_start()`` / ``_stop()`` (wrapping ``start()`` /
  ``stop()``), plus negotiated/runtime counters such as ``getOpen()``,
  ``getRetranCount()``, and ``getDropCount()``.
- The end-to-end UDP/RSSI/packetizer pattern used by regression tests is in
  ``tests/test_udpPacketizer.py`` and validates link bring-up plus frame
  integrity under injected out-of-order traffic.

Threading and Lifecycle
=======================

- ``Client`` is a wrapper; protocol-state execution runs in its internal
  ``Controller`` object.
- Concurrency-sensitive link state and counters are managed by the controller
  and surfaced through ``Client`` APIs.
- Implements a protocol-state machine internally via ``Controller`` and does
  not spin up a dedicated ``Client`` worker thread.
- Implements Managed Interface Lifecycle:
  :ref:`pyrogue_tree_node_device_managed_interfaces`

Related pages
=============

- Overview and full topology: :doc:`index`
- Transport recommendations: :doc:`/built_in_modules/protocols/network`
- C++ API: :doc:`/api/cpp/protocols/rssi/client`
