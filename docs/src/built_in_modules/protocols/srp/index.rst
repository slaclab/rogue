.. _protocols_srp:

============
SRP Protocol
============

For carrying register and memory transactions across a Rogue stream link,
Rogue provides ``rogue.protocols.srp``. SRP bridges the memory interface and
the stream interface: reads and writes are serialized into SRP frames, carried
over a stream transport, and decoded by FPGA or ASIC logic that implements the
corresponding SRP protocol.

In most deployed systems, SRP is not used by itself. It is usually combined
with a transport/reliability stack such as ``UDP -> RSSI -> Packetizer`` or a
DMA-backed stream path, with SRP providing the register-transaction semantics
on top of that stream path.

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

Where SRP Fits
==============

- SRP bridges memory transactions to stream transport.
- Tree-facing configuration and register semantics remain in PyRogue device
  definitions.
- Transport selection and tuning belong in the lower stream and protocol
  layers such as :doc:`/built_in_modules/protocols/network`,
  :doc:`/built_in_modules/protocols/udp/index`, and
  :doc:`/built_in_modules/hardware/dma/stream`.

Common Integration Patterns
===========================

- PyRogue tree pattern:
  create ``SrpV0`` or ``SrpV3``, connect it to stream transport, then pass the
  SRP object as ``memBase`` when constructing Devices.
- Standalone script pattern:
  use SRP + stream transport directly without a ``Root`` when you only need a
  narrow read/write utility path.
- Command path pattern:
  use :doc:`cmd` for opcode/context control channels that are intentionally
  separate from register-access transactions.

Related Topics
==============

- AXI stream + SRPv3 usage: :doc:`/built_in_modules/hardware/dma/stream`
- TCP memory bridge usage: :doc:`/memory_interface/tcp_bridge`
- Memory transaction model: :doc:`/memory_interface/transactions`
- Tree integration through ``memBase``: :doc:`/pyrogue_tree/core/remote_variable`

.. toctree::
   :maxdepth: 1
   :caption: SRP Protocol

   srpV0
   srpV3
   cmd
