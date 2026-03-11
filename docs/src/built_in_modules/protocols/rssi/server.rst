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

Lifecycle usage modes
=====================

- Root-managed mode:
  register interfaces with ``Root.addInterface(...)`` and let Managed
  Interface Lifecycle start/stop them.
- Standalone script mode:
  when no ``Root`` manages lifecycle, start and stop explicitly.

Standalone script pattern:

.. code-block:: python

   udp = rogue.protocols.udp.Server(0, True)
   rssi = rogue.protocols.rssi.Server(udp.maxPayload() - 8)
   udp == rssi.transport()

   rssi._start()
   try:
       # Connect upper-layer protocols and run application logic.
       pass
   finally:
       rssi._stop()
       udp._stop()

Code-backed behavior notes
==========================

- ``Server`` is a thin bundle around ``Transport``, ``Application``, and a
  server-role ``Controller`` created in ``src/rogue/protocols/rssi/Server.cpp``.
- Python bindings expose the same status and tuning APIs as client role (open
  state, counters, local parameter setters).
- In direct usage and in ``pyrogue.protocols.UdpRssiPack``, the server is
  connected as ``udp == rssi.transport()`` with upper protocols wired through
  ``rssi.application()``.

Threading and Lifecycle
=======================

- ``Server`` is a wrapper; protocol-state execution runs in its internal
  ``Controller`` object.
- Concurrency-sensitive link state and counters are managed by the controller
  and surfaced through ``Server`` APIs.
- Implements a protocol-state machine internally via ``Controller`` and does
  not spin up a dedicated ``Server`` worker thread.
- Implements Managed Interface Lifecycle:
  :ref:`pyrogue_tree_node_device_managed_interfaces`

Related Topics
=============

- Overview and full topology: :doc:`index`
- Transport recommendations: :doc:`/built_in_modules/protocols/network`

API Reference
=============

- Python: :doc:`/api/python/protocols_rssi_server`
- C++: :doc:`/api/cpp/protocols/rssi/server`
