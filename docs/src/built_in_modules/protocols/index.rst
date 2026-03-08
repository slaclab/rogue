.. _protocols:
.. _built_in_modules_protocols:

==========
Protocols
==========

Protocol modules define how stream and memory traffic is carried, framed, and
interpreted between software and firmware endpoints. They are the transport and
control layer between interface primitives and deployed system behavior.

Most Rogue systems use more than one protocol module. A common pattern is to
pair a transport protocol with a framing or transaction protocol, then map that
stack onto Stream or Memory interfaces.

Protocol selection quick guide
==============================

- Use :doc:`udp/index` for lightweight datagram transport endpoints.
- Use :doc:`rssi/index` when link reliability and ordered delivery are required.
- Use :doc:`srp/index` for register/memory transaction transport over streams.
- Use :doc:`packetizer/index` for framing, virtual channels, and packet
  routing control.
- Use :doc:`batcher/index` for record batching/unbatching transforms.
- Use :doc:`xilinx/index` for XVC/JTAG-over-TCP integration.
- Use :doc:`epicsV4/index` for EPICS PV integration helpers.
- Use :doc:`uart` for UART-backed stream/memory transport paths.

These protocol pages are most useful alongside
:doc:`/stream_interface/index` and :doc:`/memory_interface/index`, where link
construction and transaction flow are covered end to end.

.. toctree::
   :maxdepth: 1
   :caption: Protocols:

   udp/index
   rssi/index
   packetizer/index
   network
   batcher/index
   epicsV4/index
   srp/index
   xilinx/index
   uart
