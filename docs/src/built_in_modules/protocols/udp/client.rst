.. _protocols_udp_client:

===================
UDP Protocol Client
===================

``rogue::protocols::udp::Client`` is a UDP endpoint for outbound connections to
a specific remote host/port. It converts Rogue stream frames to UDP datagrams
and converts inbound datagrams back into Rogue frames.

Role in stack
=============

Use ``Client`` when Rogue software should initiate traffic to a known peer
(common for software-to-FPGA links when firmware listens on a fixed port).

Data path behavior
==================

- Outbound:
  ``acceptFrame()`` iterates frame buffers and transmits each non-empty buffer
  as a UDP datagram.
- Inbound:
  a background thread continuously calls ``recvfrom()`` and publishes received
  payloads through stream-master output.
- Oversize datagrams are dropped with warning logs if payload exceeds available
  frame space.

Construction and lifecycle
==========================

- Constructor behavior:
  resolves host address, opens socket, initializes frame pool sizing, starts
  RX thread.
- C++ ``stop()`` / Python ``_stop()``:
  disables RX thread, joins thread, and closes socket.
- ``maxPayload()``:
  inherited from ``udp::Core`` and depends on jumbo vs standard MTU mode.

Timeout and backpressure behavior
=================================

Outbound writes use ``select()`` with the configured timeout before ``sendmsg``.
If timeout elapses, a critical log is emitted and transmit retry loop continues.
Tune timeout using ``setTimeout()`` from ``udp::Core`` when needed.

Typical deployment pattern
==========================

- Software host runs Rogue UDP client.
- FPGA/remote endpoint listens on a fixed port.
- RSSI/packetizer layers sit above this transport path.
- Standalone UDP deployment is less common for control/config paths because UDP
  itself does not provide reliability or in-order delivery guarantees.

Code-backed example
===================

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
  register transport/protocol objects with ``Root.addInterface(...)`` and let
  Managed Interface Lifecycle stop them during tree shutdown.
- Standalone script mode:
  call ``_stop()`` explicitly on UDP endpoints during script teardown.

Managed lifecycle reference:
:ref:`pyrogue_tree_node_device_managed_interfaces`

Practical checklist
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

API Reference
=============

- Python: :doc:`/api/python/rogue/protocols/udp/client`
- C++: :doc:`/api/cpp/protocols/udp/client`
