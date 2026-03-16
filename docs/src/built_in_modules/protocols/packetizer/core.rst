.. _protocols_packetizer_core:

========================
Packetizer Protocol Core
========================

For packetizer v1 links, Rogue provides ``rogue.protocols.packetizer.Core``.
This class owns the packetizer v1 controller, exposes the lower transport edge
through ``transport()``, and creates per-destination application endpoints with
``application(dest)``.

Use ``Core`` when software must match an existing packetizer v1 firmware or
software peer. For new deployments where the protocol version is still open,
:doc:`coreV2` is usually the better choice.

Protocol Behavior
=================

Packetizer v1 breaks one incoming frame into one or more transport packets and
reassembles those packets on the receive side. It carries the usual AXI-Stream
sideband metadata in the wire format:

- ``TDest``
- ``TID``
- ``TUserFirst``
- ``TUserLast``
- EOF state

Each v1 packet contains:

- An 8-byte header with version, frame number, packet number, ``TDest``,
  ``TID``, and ``TUserFirst``.
- A 1-byte tail with ``TUserLast`` and EOF.

The design tradeoff is that EOF and ``TUserLast`` live in a tail rather than in
the header. That allows streaming behavior without buffering an entire packet
payload before forwarding.

Operational Notes
=================

- ``TUserLast`` is only valid when EOF is asserted.
- ``TDest``, ``TID``, and ``TUserFirst`` are repeated in each packet header
  even though they are frame-level attributes.
- Destination endpoints are allocated lazily when ``application(dest)`` is
  called.

Key Constructor Arguments
=========================

``Core(enSsi)``

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

   # Packetizer v1 core with SSI framing enabled.
   pkt = rogue.protocols.packetizer.Core(True)

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

   #include <rogue/protocols/packetizer/Core.h>

   namespace rpp = rogue::protocols::packetizer;

   int main() {
       // Packetizer v1 core with SSI framing enabled.
       auto pkt = rpp::Core::create(true);

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

``Core`` does not start its own worker thread. Packetization and
depacketization run in the caller context of the surrounding stream graph,
while lifecycle management belongs to the lower transport layer attached to
``transport()``.

Compatibility Notes
===================

- ``Core`` must connect to a packetizer v1 peer.
- If the remote endpoint expects packetizer v2, use :doc:`coreV2`.

Logging
=======

Packetizer logging is emitted by the shared controller logger:

- ``pyrogue.packetizer.Controller``
- Unified Logging API:
  ``logging.getLogger('pyrogue.packetizer').setLevel(logging.DEBUG)``
- Legacy Logging API:
  ``rogue.Logging.setFilter('pyrogue.packetizer', rogue.Logging.Debug)``

This logger is the main source for packet-drop, framing, and timeout messages.
There is no separate per-instance debug helper on ``Core``.

Related Topics
==============

- :doc:`/built_in_modules/protocols/packetizer/index`
- :doc:`/built_in_modules/protocols/packetizer/coreV2`

API Reference
=============

- Python: :doc:`/api/python/rogue/protocols/packetizer/core`
- C++: :doc:`/api/cpp/protocols/packetizer/core`
