.. _protocols:

==========
Protocols
==========

Legacy Status
=============

This is a legacy page retained during migration.
Canonical entry point: :doc:`/built_in_modules/index`.

Protocol documentation is being expanded as part of the revamp.

Current status:

- Core protocol reference pages are present and linked below.
- Several pages still need deeper narrative guidance and practical examples.

Planned expansion areas:

- Protocol selection guidance and tradeoffs
- End-to-end usage examples
- Operational notes and troubleshooting

Protocol selection quick guide
==============================

- Use :doc:`udp/index` for lightweight datagram transport endpoints.
- Use :doc:`rssi/index` when link reliability and ordered delivery are required.
- Use :doc:`srp/index` for register/memory transaction transport over streams.
- Use :doc:`packetizer/index` for framing/multiplexing control.
- Use :doc:`batcher/index` for record batching/unbatching transforms.
- Use :doc:`xilinx/index` for XVC/JTAG-over-TCP integration.
- Use :doc:`epicsV4/index` for EPICS PV integration helpers.

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
