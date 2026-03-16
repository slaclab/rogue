.. _hardware_axi:

=========================
AXI DMA Driver Wrappers
=========================

AXI hardware support in Rogue is built around wrappers for the AXI stream DMA
driver stack from
`slaclab/aes-stream-drivers <https://github.com/slaclab/aes-stream-drivers>`_.
These wrappers translate driver-level channels and register accesses into Rogue
Stream and Rogue Memory interface semantics, so hardware can be connected with
the same connection and transaction patterns used elsewhere in Rogue.

C++ API details for AXI hardware interfaces are documented in
:doc:`/api/cpp/hardware/axi/index`.

For PCIe- and DMA-backed FPGA systems, this subsection is usually the
host-side boundary between the Linux driver and the rest of the Rogue
application. The driver exposes DMA channels and a register access path, and
Rogue turns those into the same Stream and Memory abstractions used elsewhere
in the framework:

- ``AxiStreamDma`` handles moving framed data to and from DMA channels.
- ``AxiMemMap`` handles register and memory transactions through the same
  driver stack.
- Higher-level protocol choices such as RSSI, SRP, or packetizer remain
  independent of the DMA wrapper itself.

Typical integration pattern
===========================

A common host-side composition looks like this:

1. Use :doc:`memory` to expose firmware registers to a PyRogue tree or a lower
   level memory master.
2. Use :doc:`stream` to connect data-producing or data-consuming firmware
   channels into Rogue stream topologies.
3. Layer higher-level protocols such as :doc:`/built_in_modules/protocols/srp/index`
   or :doc:`/built_in_modules/protocols/rssi/index` on top of those DMA
   channels when the firmware expects them.

What To Explore Next
====================

- Stream DMA channel usage: :doc:`stream`
- Memory/register access path: :doc:`memory`
- Stream graph construction: :doc:`/stream_interface/index`
- Memory transaction routing: :doc:`/memory_interface/index`
- Protocol layering above DMA: :doc:`/built_in_modules/protocols/index`

.. toctree::
   :maxdepth: 1
   :caption: AXI Hardware:

   stream
   memory
