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

The two primary wrappers are:

- :doc:`stream`: ``AxiStreamDma`` for stream channels.
- :doc:`memory`: ``AxiMemMap`` for memory/register access.

A typical system uses both:

- ``AxiStreamDma`` carries stream traffic, often including SRP protocol frames.
- ``AxiMemMap`` exposes a memory transaction path for register reads/writes.

For most DMA-based FPGA systems this subsection is the host-side boundary
between Linux driver access and higher-level protocol/device composition in
Rogue.

.. toctree::
   :maxdepth: 1
   :caption: AXI Hardware:

   stream
   memory
