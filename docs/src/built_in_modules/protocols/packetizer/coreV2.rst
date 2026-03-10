.. _protocols_packetizer_coreV2:

==========================
Packetizer Protocol CoreV2
==========================

``CoreV2`` is the packetizer v2 wiring class. It creates a ``Transport``
endpoint and a v2 controller, then exposes ``application(dest)`` endpoints for
channel-based application routing.

Protocol behavior summary (v2)
==============================

Packetizer v2 packetizes frames similarly to v1 but adds improved structure for
interleaving packet chunks and CRC control. It also carries AXI-Stream sideband
metadata in the packetized format.

v2 format constraints and structure:

- Firmware protocol definition requires a 64-bit AXI-Stream data path for v2
  packetizer/depacketizer operation.
- Each packet has an 8-byte header and an 8-byte tail.
- Header fields include:
  version (expected ``0x2``), CRC type, ``TUserFirst``, ``TDest``, ``TID``,
  packet sequence number, and SOF flag.
- Tail fields include:
  ``TUserLast``, EOF, ``LAST_BYTE_CNT`` (valid bytes in final beat), and CRC.

CRC behavior notes (v2):

- CRC type selects no CRC, data-only CRC, or CRC over header/tail/data path as
  defined by the v2 protocol.
- In CRC-type 2 mode, CRC calculation excludes the CRC field itself.
- If firmware CRC checking is disabled, CRC field should be zero and is not
  checked on receive.
- If firmware CRC checking is enabled, peers are expected to provide valid CRC.
- Non-payload bytes in the final beat (``8 - LAST_BYTE_CNT``) still participate
  in CRC computation because they remain part of packetizer frame transfer.

Specification reference:
https://confluence.slac.stanford.edu/x/3nh4DQ

Behavior summary
================

- Constructor arguments:
  ``enIbCrc`` enables inbound CRC checking,
  ``enObCrc`` enables outbound CRC generation,
  ``enSsi`` controls SSI behavior.
- ``transport()`` returns the stream edge for lower-layer connection.
- ``application(dest)`` lazily allocates per-destination application endpoints
  for ``dest`` values ``0..255``.
- ``getDropCount()`` exposes controller-reported dropped-frame count.
- ``setTimeout()`` forwards timeout tuning into controller behavior.

When to prefer CoreV2
=====================

- New designs where packetizer version selection is open.
- Integrations requiring packetizer v2 behavior or CRC configuration control.

Code-backed example
===================

.. code-block:: python

   import rogue.protocols.packetizer

   # Packetizer v2 core:
   #   enIbCrc=True  -> validate inbound CRC
   #   enObCrc=True  -> generate outbound CRC
   #   enSsi=True    -> enable SSI framing behavior
   pkt = rogue.protocols.packetizer.CoreV2(True, True, True)

   # Destination 0 endpoint receives decoded payload frames.
   pkt.application(0) >> reg_sink

   # Outbound frames sent to destination 1.
   data_source >> pkt.application(1)

   # Attach transport side to lower protocol layer.
   # lower_layer == pkt.transport()

C++ example
===========

.. code-block:: cpp

   #include <rogue/protocols/packetizer/CoreV2.h>

   namespace rpp = rogue::protocols::packetizer;

   int main() {
       // Packetizer v2 core with inbound/outbound CRC and SSI enabled.
       auto pkt = rpp::CoreV2::create(true, true, true);

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

Packetizer v2 logs through the shared packetizer controller logger:

- ``pyrogue.packetizer.Controller``
- Unified Logging API:
  ``logging.getLogger('pyrogue.packetizer').setLevel(logging.DEBUG)``
- Legacy Logging API:
  ``rogue.Logging.setFilter('pyrogue.packetizer', rogue.Logging.Debug)``

For v2-specific debugging, this logger reports CRC/drop conditions and outbound
queue timeouts. There is no separate ``CoreV2``-specific logger name.

Compatibility note
==================

Core/CoreV2 selection must match peer endpoint expectations. Confirm protocol
version alignment across firmware and software.

In mixed system stacks, software ``CoreV2`` endpoints are typically paired with
firmware v2 packetizer/depacketizer implementations in the transport path.

See also
========

- :doc:`/built_in_modules/protocols/packetizer/index`
- :doc:`/built_in_modules/protocols/packetizer/core`
- :doc:`/api/cpp/protocols/packetizer/coreV2`
