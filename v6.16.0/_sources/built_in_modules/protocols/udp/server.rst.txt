.. _protocols_udp_server:

===================
UDP Protocol Server
===================

For UDP links where Rogue should listen on a local port and wait for the remote
side to initiate traffic, Rogue provides ``rogue::protocols::udp::Server``.
This form is most common in tests, software peer links, and other
remote-initiated deployments.

``Server`` binds a local UDP port, emits inbound datagrams into the Rogue
stream graph, and sends outbound datagrams to the most recently observed peer.

Role In The Stack
=================

Use ``Server`` when Rogue should act as the listener rather than the initiator.
That is less common than ``Client`` for FPGA links, but useful for integration
tests or peer-to-peer software setups.

Construction
============

``Server(port, jumbo)`` is shaped by two constructor arguments:

- ``port``
  Local UDP port to bind. ``0`` requests an OS-assigned port.
- ``jumbo``
  Select jumbo payload sizing when ``True`` and standard MTU sizing when
  ``False``.

The constructor creates and binds the socket, initializes the frame pool, and
starts the background receive thread. When ``port=0``, use ``getPort()`` to
discover the assigned local port.

Data Path Behavior
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

Lifecycle And Transport Behavior
================================

- ``getPort()``
  Returns the bound local UDP port.
- C++ ``stop()`` / Python ``_stop()``
  Stops the receive thread, joins it, and closes the socket.
- ``setTimeout()``
  Inherited from ``udp::Core`` and used for outbound transmit readiness checks.

Timeout Behavior
================

Outbound writes use ``select()`` with configured timeout. If transmit readiness
does not occur in time, server logs a critical timeout and retries.

When To Use ``Server``
======================

- Rogue process binds a local UDP port.
- Remote endpoint initiates traffic toward that port.
- Upper layers (RSSI/packetizer) use the server transport endpoint.
- Standalone UDP deployment is less common for control/config paths because UDP
  itself does not provide reliability or in-order delivery guarantees.

Python Example
==============

.. code-block:: python

   import rogue.protocols.udp

   src = MyFrameSource()  # Application stream source.
   dst = MyFrameSink()    # Application stream sink.
   udp = rogue.protocols.udp.Server(0, True)

   # Outbound application traffic: source -> UDP datagrams.
   src >> udp

   # Inbound application traffic: UDP datagrams -> sink.
   udp >> dst

Lifecycle usage modes:

- Root-managed mode:
  Register transport/protocol objects with ``Root.addInterface(...)`` and let
  Managed Interface Lifecycle stop them during tree shutdown.
- Standalone script mode:
  Call ``_stop()`` explicitly on UDP endpoints during script teardown.

Managed lifecycle reference:
:ref:`pyrogue_tree_node_device_managed_interfaces`

C++ Example
===========

.. code-block:: cpp

   #include <rogue/protocols/udp/Server.h>

   namespace rpu = rogue::protocols::udp;

   auto udp = rpu::Server::create(0, true);

   src >> udp;
   udp >> dst;

   auto port = udp->getPort();
   udp->stop();

Practical Checklist
===================

- Reserve and expose the local bind port.
- Confirm firewall/NAT rules allow inbound UDP packets.
- Ensure expected peer address/port behavior is defined for your system.
- In multi-peer environments, account for "last sender wins" peer update model.

Related Topics
==============

- :doc:`/built_in_modules/protocols/udp/index`
- :doc:`/built_in_modules/protocols/network`
- :doc:`/built_in_modules/protocols/rssi/index`
- :doc:`client`

API Reference
=============

- Python: :doc:`/api/python/rogue/protocols/udp/server`
- C++: :doc:`/api/cpp/protocols/udp/server`
