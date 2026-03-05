.. _protocols_udp:

============
UDP Protocol
============

UDP provides datagram transport for stream traffic. In Rogue systems, UDP is
normally used as a transport layer under RSSI and packetizer rather than as a
standalone reliability layer.

Where UDP fits in the stack
===========================

Typical protocol stack:

.. code-block:: text

   UDP <-> RSSI <-> Packetizer <-> Application logic

Use UDP directly only when datagram delivery semantics are acceptable for your
application. For ordered/reliable link behavior, use RSSI on top of UDP.

UDP classes and responsibilities
================================

The ``rogue::protocols::udp`` layer is split into:

- ``Core``:
  shared transport configuration (payload sizing, socket timeout, RX buffer
  tuning). See :doc:`/api/cpp/protocols/udp/core`.
- ``Client``:
  outbound endpoint to a specific remote host/port. See :doc:`client` and
  :doc:`/api/cpp/protocols/udp/client`.
- ``Server``:
  local bind endpoint that receives inbound datagrams and can transmit to the
  most recently observed peer. See :doc:`server` and
  :doc:`/api/cpp/protocols/udp/server`.

Payload sizing and MTU
======================

``udp::Core.maxPayload()`` sets frame payload limits by MTU mode:

- jumbo mode (``jumbo=True``): ``8972`` bytes payload
- standard mode (``jumbo=False``): ``1472`` bytes payload

When UDP is used under RSSI, RSSI payload is typically derived from UDP payload
budget (for example ``udp.maxPayload() - 8`` as used in integration tests and
wrapper patterns).

Threading and lifecycle
=======================

- ``Client`` and ``Server`` each start a background RX thread at construction.
- ``stop()`` joins the thread and closes the socket.
- ``Core`` does not define a separate managed start/stop state machine.

Overview
========

Each endpoint is both:

- a stream ``Slave`` (accepts outbound frames and transmits UDP datagrams)
- a stream ``Master`` (publishes inbound datagrams as frames)

This dual-role model allows direct insertion into Rogue stream graphs.

When to use
===========

- You need lightweight datagram transport over IP networks.
- Your reliability and framing requirements are handled by upper layers.
- You are integrating with existing UDP-based firmware endpoints.

When not to use directly
========================

- If you need ordered/reliable delivery semantics by default, use RSSI over
  UDP instead of raw UDP-only application flows.
- If you need transaction-level memory semantics, use SRP on top of stream
  transport rather than direct UDP framing.

Code-backed integration example
===============================

The following pattern mirrors ``tests/test_udpPacketizer.py``:

.. code-block:: python

   import rogue.protocols.udp
   import rogue.protocols.rssi
   import rogue.protocols.packetizer

   serv = rogue.protocols.udp.Server(0, True)
   cli = rogue.protocols.udp.Client("127.0.0.1", serv.getPort(), True)

   s_rssi = rogue.protocols.rssi.Server(serv.maxPayload())
   c_rssi = rogue.protocols.rssi.Client(cli.maxPayload())

   s_pkt = rogue.protocols.packetizer.CoreV2(True, True, True)
   c_pkt = rogue.protocols.packetizer.CoreV2(True, True, True)

   cli == c_rssi.transport()
   c_rssi.application() == c_pkt.transport()
   serv == s_rssi.transport()
   s_rssi.application() == s_pkt.transport()

Related docs
============

- :ref:`protocols_network`
- :doc:`/protocols/network`
- :doc:`/protocols/rssi/index`
- :doc:`/protocols/packetizer/index`
- :doc:`/protocols/srp/index`

C++ API details for UDP protocol classes are documented in
:doc:`/api/cpp/protocols/udp/index`.

.. toctree::
   :maxdepth: 1
   :caption: UDP Protocol

   client
   server
