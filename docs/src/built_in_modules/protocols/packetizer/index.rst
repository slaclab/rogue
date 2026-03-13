.. _protocols_packetizer:

===================
Packetizer Protocol
===================

For carrying multiple logical application streams over one shared transport
path, Rogue provides ``rogue.protocols.packetizer``. Packetizer sits above a
lower transport such as RSSI, DMA, or PGP and turns that shared link into a
set of destination-addressed application channels.

In practice, packetizer is the layer that lets one physical transport session
carry different traffic types at the same time, such as register transactions,
waveform data, and diagnostic events. The receive side can then reconstruct the
original frame boundaries and route each stream to the correct destination
endpoint.

In many systems, a software packetizer endpoint in Rogue connects directly to a
firmware packetizer endpoint. That is what preserves AXI-Stream sideband
metadata such as destination and user fields while traffic crosses an external
transport.

Protocol Specifications
=======================

- Packetizer v1 specification: https://confluence.slac.stanford.edu/x/1oyfD
- Packetizer v2 specification: https://confluence.slac.stanford.edu/x/3nh4DQ

How Packetizer Fits In The Stack
================================

A common network-backed stack looks like this:

.. code-block:: text

   UDP <-> RSSI <-> Packetizer <-> Application endpoints

On DMA-backed systems, the lower side might instead be:

.. code-block:: text

   AxiStreamDma <-> Packetizer <-> Application endpoints

Both packetizer core variants expose the same main structure:

- ``transport()`` is the lower-layer edge facing RSSI, UDP, DMA, or another
  transport path.
- ``application(dest)`` is the upper-layer edge for one application channel.
- A controller in the middle packetizes outbound frames and depacketizes
  inbound ones.

The destination field is an 8-bit selector, so one transport session can carry
up to 256 logical application channels. In real designs, that lets software and
firmware share one lower transport while still separating register, data, and
debug traffic cleanly.

Packetizer Versions At A Glance
===============================

- ``Core`` implements packetizer v1.
  It uses an 8-byte header and a compact 1-byte tail carrying ``TUserLast`` and
  EOF information.
- ``CoreV2`` implements packetizer v2.
  It keeps the same overall role but adds a more structured 64-bit tail,
  interleaving support, and configurable CRC behavior.

Subtopics
=========

- :doc:`core`
  Use packetizer v1 when the peer requires the older v1 wire format.
- :doc:`coreV2`
  Use packetizer v2 for new designs or whenever the link already standardizes on
  v2 behavior and CRC handling.

Version Selection
=================

Packetizer version is a compatibility choice, not just a software preference.
Both ends of the link must agree on the same wire format.

- Use ``Core`` when the peer expects packetizer v1.
- Use ``CoreV2`` when the peer expects packetizer v2.
- Do not mix v1 and v2 endpoints across the same link.

If the version is still open, ``CoreV2`` is usually the better default. If the
firmware side is already fixed, match that firmware.

End-To-End Example
==================

The packetizer path in ``tests/test_udpPacketizer.py`` shows the usual shape of
the stack. Packetizer sits above RSSI, and one application destination carries
the test traffic:

.. code-block:: python

   import rogue.protocols.packetizer
   import rogue.protocols.rssi
   import rogue.utilities

   # Lower transport/reliability layer.
   rssi = rogue.protocols.rssi.Client(1472 - 8)

   # Packetizer layer. This example uses v2 with inbound and outbound CRC.
   pkt = rogue.protocols.packetizer.CoreV2(True, True, True)

   # Source and sink connected to destination channel 0.
   tx = rogue.utilities.Prbs()
   rx = rogue.utilities.Prbs()

   # Outbound traffic enters packetizer on application destination 0.
   tx >> pkt.application(0)

   # Packetizer transport side connects bidirectionally to RSSI.
   rssi.application() == pkt.transport()

   # Inbound traffic for destination 0 is delivered to the receiver.
   pkt.application(0) >> rx

Threading And Lifecycle
=======================

Packetizer core objects are wiring helpers. They do not start their own worker
threads, and they do not define a standalone start or stop API in Python.

Lifecycle control usually belongs to the lower transport layer that packetizer
attaches to:

- RSSI endpoints own protocol lifecycle and background activity.
- UDP endpoints own socket lifecycle.
- DMA wrappers own driver-facing threads.

If a packetizer path is misbehaving, the lower layer is often the first place
to inspect.

Related Topics
==============

- :doc:`/built_in_modules/protocols/network`
- :doc:`/built_in_modules/protocols/rssi/index`
- :doc:`/built_in_modules/protocols/udp/index`
- :doc:`/built_in_modules/hardware/dma/stream`
- :doc:`/built_in_modules/protocols/batcher/index`

API Reference
=============

- C++: :doc:`/api/cpp/protocols/packetizer/index`
- Python:
  :doc:`/api/python/rogue/protocols/packetizer/application`
  :doc:`/api/python/rogue/protocols/packetizer/transport`
  :doc:`/api/python/rogue/protocols/packetizer/core`
  :doc:`/api/python/rogue/protocols/packetizer/corev2`

.. toctree::
   :maxdepth: 1
   :caption: Packetizer Protocol

   core
   coreV2
