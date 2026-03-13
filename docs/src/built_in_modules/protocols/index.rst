.. _protocols:
.. _built_in_modules_protocols:

==========
Protocols
==========

Protocols defines how stream and memory traffic are carried, framed, and acted
on between software and firmware endpoints. These pages are mostly
``rogue.protocols.*``-first, but they also call out the small number of common
``pyrogue.protocols.*`` wrappers and Python-only helpers where that is how
users usually encounter the protocol.

Most deployments combine multiple protocol layers. A typical stack starts with
hardware or a socket transport, adds reliability or framing, then adds a
transaction protocol such as SRP before it connects into a Memory or Stream
topology.

Subtopics
=========

- Use :doc:`udp/index` for lightweight datagram transport endpoints.
- Use :doc:`rssi/index` for ordered, reliable delivery over packet links.
- Use :doc:`network` for the common ``pyrogue.protocols.UdpRssiPack`` wrapper
  that assembles a typical UDP/RSSI transport stack.
- Use :doc:`srp/index` for register and memory transaction transport over
  streams.
- Use :doc:`packetizer/index` for framing, virtual channels, and packet routing
  control.
- Use :doc:`batcher/index` for batching and unbatching transforms on stream
  traffic.
- Use :doc:`xilinx/index` for XVC and related Xilinx JTAG-over-network support.
- Use :doc:`epicsV4/index` for EPICS PV integration helpers.
- Use :doc:`uart` for UART-backed stream or memory transport paths.
- Use :doc:`gpib` for SCPI-style instrument control over GPIB.

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
   gpib
