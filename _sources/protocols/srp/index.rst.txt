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


.. toctree::
   :maxdepth: 1
   :caption: SRP Protocol

   srpV0
   srpV3
   cmd
   classes/index
