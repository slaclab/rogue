.. _protocols_udp_server:

===================
UDP Protocol Server
===================

``rogue::protocols::udp::Server`` is a UDP endpoint that binds a local port,
receives inbound datagrams, and emits them into the Rogue stream graph.

Role in stack
=============

Use ``Server`` when Rogue should listen for remote-initiated traffic, such as
software peer links and integration tests.

Data path behavior
==================

- Inbound:
  RX thread blocks on ``recvfrom()``, converts datagrams to stream frames, and
  forwards them to connected stream consumers.
- Peer tracking:
  server updates its remote endpoint to the most recently observed packet
  source; outbound sends target that endpoint.
- Outbound:
  ``acceptFrame()`` sends non-empty frame buffers as UDP datagrams to current
  remote endpoint.

Construction and lifecycle
==========================

- Constructor behavior:
  creates socket, binds local port, starts RX thread.
- Dynamic port assignment:
  passing ``port=0`` requests an OS-assigned port, retrievable via ``getPort()``.
- ``stop()``:
  disables RX thread, joins thread, and closes socket.

Timeout behavior
================

Outbound writes use ``select()`` with configured timeout. If transmit readiness
does not occur in time, server logs a critical timeout and retries.

Typical deployment pattern
==========================

- Rogue process binds a local UDP port.
- Remote endpoint initiates traffic toward that port.
- Upper layers (RSSI/packetizer) use the server transport endpoint.

Code-backed example
===================

.. code-block:: python

   import rogue.protocols.udp
   import rogue.protocols.rssi

   udp = rogue.protocols.udp.Server(0, True)
   rssi = rogue.protocols.rssi.Server(udp.maxPayload() - 8)

   udp == rssi.transport()
   rssi._start()

Practical checklist
===================

- Reserve and expose the local bind port.
- Confirm firewall/NAT rules allow inbound UDP packets.
- Ensure expected peer address/port behavior is defined for your system.
- In multi-peer environments, account for "last sender wins" peer update model.

Related docs
============

- :doc:`/built_in_modules/protocols/udp/index`
- :doc:`/built_in_modules/protocols/network`
- :doc:`/built_in_modules/protocols/rssi/index`
- :doc:`/api/cpp/protocols/udp/server`
