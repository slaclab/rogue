.. _protocols_packetizer:

===================
Packetizer Protocol
===================

Packetizer provides frame formatting and destination-channel multiplexing above
transport/reliability layers. In practice it is commonly placed above RSSI
(which is often above UDP) to route application traffic by virtual channel.

Typical stack position
======================

.. code-block:: text

   UDP <-> RSSI <-> Packetizer <-> Application endpoints (dest 0..255)

Core model
==========

Both packetizer core variants wire the same main components:

- ``Transport``:
  stream edge facing lower transport layers.
- ``Controller``:
  protocol processing engine (v1 or v2 implementation).
- ``Application(dest)``:
  per-destination stream endpoints (0-255).

Overview
========

The core object creates and connects these components, and application channels
are instantiated lazily when ``application(dest)`` is called.

Choosing a core version
=======================

- Use :doc:`core` when existing systems require packetizer v1 compatibility.
- Use :doc:`coreV2` for new designs or links standardized on packetizer v2.
- Ensure both peers use matching packetizer behavior/version expectations.

Integration pattern
===================

The following pattern mirrors ``tests/test_udpPacketizer.py``:

.. code-block:: python

   import rogue.protocols.packetizer
   import rogue.protocols.rssi

   rssi = rogue.protocols.rssi.Client(1472 - 8)
   pkt = rogue.protocols.packetizer.CoreV2(True, True, True)

   rssi.application() == pkt.transport()
   pkt.application(0) >> my_sink
   my_source >> pkt.application(0)

Core variants
=============

- ``Core``: baseline packetizer implementation for standard deployments.
- ``CoreV2``: newer packetizer variant with updated protocol behavior and
  compatibility needs.

When to use
===========

- You need explicit packet framing at the protocol layer.
- You need destination/application channel routing semantics.
- You are integrating with systems that already use Rogue packetizer endpoints.
- You want a single transport session to carry multiple logical channels.

Related docs
============

- :doc:`/built_in_modules/protocols/network`
- :doc:`/built_in_modules/protocols/rssi/index`
- :doc:`/built_in_modules/protocols/udp/index`
- :doc:`/stream_interface/index`

C++ API details for packetizer protocol classes are documented in
:doc:`/api/cpp/protocols/packetizer/index`.

.. toctree::
   :maxdepth: 1
   :caption: Packetizer Protocol

   core
   coreV2
