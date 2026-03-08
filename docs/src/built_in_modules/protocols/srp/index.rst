.. _protocols_srp:

============
SRP Protocol
============

Rogue SRP components provide a bridge between the memory transaction API and
the stream API. Memory reads/writes are serialized into SRP stream frames,
transported over a link (for example DMA or TCP), and consumed by FPGA/ASIC
logic that implements the SRP protocol for register access.

Rogue documentation focuses on integration and usage. The wire-format protocol
specifications are maintained externally:

- SRPv0: https://confluence.slac.stanford.edu/x/aRmVD
- SRPv3: https://confluence.slac.stanford.edu/x/cRmVD

C++ API details for SRP protocol classes are documented in
:doc:`/api/cpp/protocols/srp/index`.

Choosing SRP version
====================

- Use :doc:`srpV3` for current systems unless compatibility requires v0.
- Use :doc:`srpV0` only when endpoint firmware is locked to v0 framing.
- Use :doc:`cmd` for lightweight command opcodes rather than register access.

Integration boundaries
======================

- SRP bridges memory transactions to stream transport.
- Tree-facing configuration and register semantics remain in PyRogue device
  definitions.
- Stream transport tuning belongs in :doc:`/stream_interface/index`.

Related integration pages
=========================

- AXI stream + SRPv3 usage: :doc:`/built_in_modules/hardware/dma/stream`
- TCP memory bridge usage: :doc:`/memory_interface/tcp_bridge`

.. toctree::
   :maxdepth: 1
   :caption: SRP Protocol

   srpV0
   srpV3
   cmd
