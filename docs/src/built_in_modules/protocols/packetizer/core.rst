.. _protocols_packetizer_core:

========================
Packetizer Protocol Core
========================

``Core`` is the packetizer v1 wiring class. It creates a ``Transport`` endpoint
and a v1 controller, then exposes ``application(dest)`` endpoints for channel-
based application routing.

Protocol behavior summary (v1)
==============================

Packetizer v1 breaks one incoming frame into one or more packets and reassembles
packets back into the original frame on the receive side. AXI-Stream sideband
values (``TDest``, ``TID``, ``TUserFirst``, ``TUserLast``) are carried in the
packetized wire format.

Each packet has:

- An 8-byte header, including:
  version (expected ``0``), frame number, packet number, ``TDest``, ``TID``,
  and ``TUserFirst``.
- A 1-byte tail, including:
  ``TUserLast`` (7 bits) and EOF flag (MSB).

Operational notes:

- ``TUserLast`` is only valid when EOF is asserted.
- Putting EOF/``TUserLast`` in a tail allows streaming operation without
  buffering a full packet payload before forwarding.
- ``TDest``, ``TID``, and ``TUserFirst`` are repeated in each packet header,
  even though they are frame-level attributes.

Specification reference:
https://confluence.slac.stanford.edu/x/1oyfD

Behavior summary
================

- Constructor argument ``enSsi`` controls SSI framing behavior.
- ``transport()`` returns the stream edge for lower-layer connection.
- ``application(dest)`` lazily allocates per-destination application endpoints
  for ``dest`` values ``0..255``.
- ``getDropCount()`` exposes controller-reported dropped-frame count.
- ``setTimeout()`` forwards timeout tuning into controller behavior.

Compatibility notes
===================

- Packetizer v1 must be matched by a packetizer v1 peer.
- Use :doc:`coreV2` for newer v2 deployments, interleaving support, and CRC
  control options.

When to prefer Core
===================

- Existing firmware/software integration expects packetizer v1 behavior.
- You are extending an already-deployed stack already based on ``Core``.

Code-backed example
===================

.. code-block:: python

   import rogue.protocols.packetizer

   # Packetizer v1 core with SSI framing behavior enabled.
   pkt = rogue.protocols.packetizer.Core(True)

   # Destination 0 endpoint receives decoded payload frames.
   pkt.application(0) >> reg_sink

   # Outbound frames sent to destination 1.
   data_source >> pkt.application(1)

   # Attach transport side to lower protocol layer.
   # lower_layer == pkt.transport()

C++ example
===========

.. code-block:: cpp

   #include <rogue/protocols/packetizer/Core.h>

   namespace rpp = rogue::protocols::packetizer;

   int main() {
       // Packetizer v1 core with SSI framing enabled.
       auto pkt = rpp::Core::create(true);

       // Example lower-layer connection:
       // *lowerLayer == pkt->transport();

       // Example destination endpoint access:
       auto app0 = pkt->application(0);
       (void)app0;

       // Query controller drop counter for diagnostics.
       auto dropCount = pkt->getDropCount();
       (void)dropCount;
       return 0;
   }

Logging
=======

Packetizer logging is emitted by the shared controller via Rogue C++ logging.

Static logger name:

- ``pyrogue.packetizer.Controller``

Enable it before constructing packetizer objects:

.. code-block:: python

   import rogue

   rogue.Logging.setFilter('pyrogue.packetizer', rogue.Logging.Debug)

This logger is the main source for packet drop, framing, and queue timeout
messages. There is no additional per-instance debug helper on ``Core``.

Related Topics
==============

- :doc:`/built_in_modules/protocols/packetizer/index`
- :doc:`/built_in_modules/protocols/packetizer/coreV2`

API Reference
=============

- Python: :doc:`/api/python/rogue/protocols/packetizer_core`
- C++: :doc:`/api/cpp/protocols/packetizer/core`
