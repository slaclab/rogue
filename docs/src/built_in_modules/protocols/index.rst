.. _protocols:
.. _built_in_modules_protocols:

==========
Protocols
==========

This subsection of :doc:`/built_in_modules/index` covers transport and control
protocol layers used in Rogue systems. These pages focus on protocol behavior,
composition patterns, and usage notes that connect stream and memory
interfaces to deployed workflows.

Protocol selection quick guide
==============================

- Use :doc:`udp/index` for lightweight datagram transport endpoints.
- Use :doc:`rssi/index` when link reliability and ordered delivery are required.
- Use :doc:`srp/index` for register/memory transaction transport over streams.
- Use :doc:`packetizer/index` for framing/multiplexing control.
- Use :doc:`batcher/index` for record batching/unbatching transforms.
- Use :doc:`xilinx/index` for XVC/JTAG-over-TCP integration.
- Use :doc:`epicsV4/index` for EPICS PV integration helpers.

What To Explore Next
====================

- Built-in modules overview and section context: :doc:`/built_in_modules/index`
- Stream interface fundamentals and connection patterns: :doc:`/stream_interface/index`
- Memory interface routing and transaction flow: :doc:`/memory_interface/index`

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
