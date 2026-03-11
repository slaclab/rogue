.. _protocols_packetizer:

===================
Packetizer Protocol
===================

Packetizer provides frame formatting and destination-channel multiplexing above
transport/reliability layers. It packetizes large stream frames into smaller
transport-friendly packets, then depacketizes them back into original frames on
the receive side. In practice it is commonly placed above RSSI (which is often
above UDP) to route application traffic by virtual channel. It lets one
physical transport path carry multiple logical application streams without
requiring separate sockets or DMA channels per flow.
Each packet carries frame metadata (such as destination/virtual channel and
other sideband fields), so receivers can correctly demultiplex mixed traffic
streams after transport.

In many systems, software packetizer endpoints in Rogue connect to firmware
packetizer endpoints (for example in the SURF firmware library). This allows
AXI-Stream sideband metadata to be preserved while sending frame traffic over
external transports such as UDP, PGP, or DMA-backed links.

Protocol specifications
=======================

- Packetizer v1 specification: https://confluence.slac.stanford.edu/x/1oyfD
- Packetizer v2 specification: https://confluence.slac.stanford.edu/x/3nh4DQ

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

Protocol versions at a glance
=============================

- ``Core`` (v1):
  packet header includes version/frame/packet counters plus
  ``TDest``/``TID``/``TUserFirst`` and uses a compact 1-byte tail with
  ``TUserLast`` + EOF bit.
- ``CoreV2`` (v2):
  designed for interleaving packet chunks and adds a structured 64-bit tail
  including ``TUserLast``, EOF, ``LAST_BYTE_CNT``, and CRC field support.

Overview
========

The core object creates and connects these components, and application channels
are instantiated lazily when ``application(dest)`` is called.
The ``dest`` field is an 8-bit channel selector (0-255), so stream graphs can
separate traffic types (for example register transactions, waveform data, and
diagnostic events) while sharing one lower transport path.

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

   # Lower protocol layer (reliability + transport).
   rssi = rogue.protocols.rssi.Client(1472 - 8)

   # Packetizer core (v2) with inbound CRC check, outbound CRC generation, SSI.
   pkt = rogue.protocols.packetizer.CoreV2(True, True, True)

   # Connect lower layer into packetizer transport edge.
   rssi.application() == pkt.transport()

   # Route destination 0 to a register/control sink.
   pkt.application(0) >> my_sink

   # Route source traffic into destination 0 channel.
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

Lifecycle notes
===============

Packetizer core objects are data-path wiring/helpers and do not define a
separate start API in Python. Lifecycle management is usually applied to the
lower transport/reliability interfaces (for example RSSI, UDP, DMA) that
packetizer attaches to.

Related docs
============

- :doc:`/built_in_modules/protocols/network`
- :doc:`/built_in_modules/protocols/rssi/index`
- :doc:`/built_in_modules/protocols/udp/index`
- :doc:`/stream_interface/index`
- :doc:`/built_in_modules/protocols/batcher/index`

C++ API details for packetizer protocol classes are documented in
:doc:`/api/cpp/protocols/packetizer/index`.

Python API details for packetizer protocol classes are documented in:

- :doc:`/api/python/protocols_packetizer_application`
- :doc:`/api/python/protocols_packetizer_transport`
- :doc:`/api/python/protocols_packetizer_core`
- :doc:`/api/python/protocols_packetizer_corev2`

.. toctree::
   :maxdepth: 1
   :caption: Packetizer Protocol

   core
   coreV2
