.. _protocols_udp_client:

===================
UDP Protocol Client
===================

For Rogue software that should initiate traffic to a known remote host and
port, Rogue provides ``rogue::protocols::udp::Client``. This is the usual UDP
form for software-to-FPGA links when firmware listens on a fixed port.

``Client`` converts outbound Rogue stream frames into UDP datagrams and
converts inbound UDP datagrams back into Rogue frames.

Role In The Stack
=================

Use ``Client`` when Rogue should act as the peer that knows the remote address
up front. In practice, that is the common deployment model for FPGA links that
run UDP underneath RSSI and packetizer.

Construction
============

``Client(host, port, jumbo)`` is shaped by three constructor arguments:

- ``host``
  Remote hostname or IPv4 address.
- ``port``
  Remote UDP port.
- ``jumbo``
  Select jumbo payload sizing when ``True`` and standard MTU sizing when
  ``False``.

The constructor resolves the host address, opens the socket, sizes the local
frame pool from the MTU mode, and starts the background receive thread.

Data Path Behavior
==================

- Outbound:
  ``acceptFrame()`` iterates frame buffers and transmits each non-empty buffer
  as a UDP datagram.
- Inbound:
  a background thread continuously calls ``recvfrom()`` and publishes received
  payloads through stream-master output.
- Oversize datagrams are dropped with warning logs if payload exceeds available
  frame space.

Lifecycle And Transport Behavior
================================

- ``maxPayload()``
  Inherited from ``udp::Core`` and depends on jumbo vs standard MTU mode.
- C++ ``stop()`` / Python ``_stop()``
  Stops the receive thread, joins it, and closes the socket.
- ``setTimeout()``
  Inherited from ``udp::Core`` and used for outbound transmit readiness checks.

Timeout And Backpressure
========================

Outbound writes use ``select()`` with the configured timeout before ``sendmsg``.
If timeout elapses, a critical log is emitted and transmit retry loop continues.
Tune timeout using ``setTimeout()`` from ``udp::Core`` when needed.

When To Use ``Client``
======================

- Software host runs Rogue UDP client.
- FPGA/remote endpoint listens on a fixed port.
- RSSI/packetizer layers sit above this transport path.
- Standalone UDP deployment is less common for control/config paths because UDP
  itself does not provide reliability or in-order delivery guarantees.

Python Example
==============

.. code-block:: python

   import rogue.protocols.udp

   src = MyFrameSource()  # Application stream source.
   dst = MyFrameSink()    # Application stream sink.
   udp = rogue.protocols.udp.Client("10.0.0.5", 8192, True)

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

   #include <rogue/protocols/udp/Client.h>

   namespace rpu = rogue::protocols::udp;

   auto udp = rpu::Client::create("10.0.0.5", 8192, true);

   src >> udp;
   udp >> dst;

   udp->stop();

Practical Checklist
===================

- Confirm target host/IP and port.
- Confirm MTU/jumbo-frame assumptions match both endpoints.
- Confirm firewall and routing allow bidirectional UDP traffic.
- Ensure upper protocol payload sizing fits ``maxPayload()`` budget.

Related Topics
==============

- :doc:`/built_in_modules/protocols/udp/index`
- :doc:`/built_in_modules/protocols/network`
- :doc:`/built_in_modules/protocols/rssi/index`
- :doc:`server`

API Reference
=============

- Python: :doc:`/api/python/rogue/protocols/udp/client`
- C++: :doc:`/api/cpp/protocols/udp/client`
