.. _protocols_packetizer_coreV2:

==========================
Packetizer Protocol CoreV2
==========================

For packetizer v2 links, Rogue provides ``rogue.protocols.packetizer.CoreV2``.
This class owns the v2 controller, exposes the lower transport edge through
``transport()``, and creates per-destination application endpoints with
``application(dest)``.

Use ``CoreV2`` for new packetizer deployments, or whenever the peer already
expects the v2 wire format.

Protocol Behavior
=================

Packetizer v2 serves the same routing role as v1 but adds a more structured
tail format, better support for interleaving packet chunks, and configurable
CRC behavior.

Important v2 format traits:

- The firmware protocol assumes a 64-bit AXI-Stream datapath.
- Each packet has an 8-byte header and an 8-byte tail.
- The header includes version, CRC type, ``TUserFirst``, ``TDest``, ``TID``,
  packet sequence number, and SOF information.
- The tail includes ``TUserLast``, EOF, ``LAST_BYTE_CNT``, and CRC.

CRC Behavior
============

CRC handling is one of the main reasons to choose v2. The CRC mode is a
link-level compatibility choice, so software and firmware must agree on how CRC
is generated and checked.

Practical points:

- ``enIbCrc`` enables inbound CRC checking in software.
- ``enObCrc`` enables outbound CRC generation in software.
- The v2 protocol allows different CRC modes, including no CRC and full-path
  CRC behavior as defined by the specification.
- If firmware is not checking CRC, the field may be ignored or expected to be
  zero depending on the peer implementation.

Key Constructor Arguments
=========================

``CoreV2(enIbCrc, enObCrc, enSsi)``

- ``enIbCrc`` enables inbound CRC checking.
- ``enObCrc`` enables outbound CRC generation.
- ``enSsi`` enables SSI framing behavior.

Common Controls
===============

- ``transport()`` returns the lower-layer stream edge.
- ``application(dest)`` returns the destination endpoint for values ``0..255``.
- ``getDropCount()`` reports the controller drop count.
- ``setTimeout(timeout)`` forwards timeout tuning into the controller, in
  microseconds.

Python Example
==============

.. code-block:: python

   import rogue.protocols.packetizer
   import rogue.protocols.rssi

   # Packetizer v2 core:
   #   enIbCrc=True  -> validate inbound CRC
   #   enObCrc=True  -> generate outbound CRC
   #   enSsi=True    -> enable SSI framing behavior
   pkt = rogue.protocols.packetizer.CoreV2(True, True, True)

   # Lower protocol layer.
   rssi = rogue.protocols.rssi.Client(1472 - 8)
   rssi.application() == pkt.transport()

   # Outbound traffic enters destination channel 1.
   data_source >> pkt.application(1)

   # Inbound traffic from destination channel 0 is delivered to a sink.
   pkt.application(0) >> reg_sink

C++ Example
===========

.. code-block:: cpp

   #include <rogue/protocols/packetizer/CoreV2.h>

   namespace rpp = rogue::protocols::packetizer;

   int main() {
       // Packetizer v2 core with inbound CRC, outbound CRC, and SSI enabled.
       auto pkt = rpp::CoreV2::create(true, true, true);

       // Access one application destination endpoint.
       auto app0 = pkt->application(0);
       (void)app0;

       // Query drop count for diagnostics.
       auto dropCount = pkt->getDropCount();
       (void)dropCount;

       // Lower-layer connection would be made through pkt->transport().
       return 0;
   }

Threading And Lifecycle
=======================

``CoreV2`` does not start its own worker thread. Packetizer lifecycle still
belongs to the lower transport layer attached to ``transport()``.

Compatibility Notes
===================

- ``CoreV2`` must connect to a packetizer v2 peer.
- If the remote endpoint expects packetizer v1, use :doc:`core`.

In mixed system stacks, software ``CoreV2`` endpoints are commonly paired with
firmware v2 packetizer or depacketizer implementations in the transport path.

Logging
=======

Packetizer v2 logs through the same controller logger used by v1:

- ``pyrogue.packetizer.Controller``

Enable it before constructing packetizer objects:

.. code-block:: python

   import rogue

   rogue.Logging.setFilter('pyrogue.packetizer', rogue.Logging.Debug)

This logger reports CRC failures, packet drops, and queue timeout conditions.
There is no separate ``CoreV2``-specific logger name.

Related Topics
==============

- :doc:`/built_in_modules/protocols/packetizer/index`
- :doc:`/built_in_modules/protocols/packetizer/core`

API Reference
=============

- Python: :doc:`/api/python/rogue/protocols/packetizer/corev2`
- C++: :doc:`/api/cpp/protocols/packetizer/coreV2`
