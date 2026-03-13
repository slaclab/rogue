.. _hardware:
.. _built_in_modules_hardware:

========
Hardware
========

Hardware collects the driver-backed endpoints that connect Rogue to concrete
firmware and PCIe data paths. These pages are ``rogue.hardware.*``-first. They
describe the low-level objects that bridge host software into stream or memory
channels before higher-level protocol logic is applied.

Hardware selection is usually driven first by the platform and driver you have
available, then by whether you need a stream DMA path, a memory-mapped path, or
raw access to a device-specific endpoint.

The driver stack required to use these interfaces is available at:

https://github.com/slaclab/aes-stream-drivers

Choosing A Hardware Family
==========================

- Use :doc:`dma/index` for AXI DMA-backed stream and memory endpoints such as
  ``rogue.hardware.axi.AxiStreamDma`` and ``rogue.hardware.axi.AxiMemMap``.
- Use :doc:`raw/index` for raw hardware memory access through
  ``rogue.hardware.MemMap``.

After choosing a hardware endpoint, continue with
:doc:`/built_in_modules/protocols/index` to select transport and framing
behavior, then use :doc:`/stream_interface/index` or
:doc:`/memory_interface/index` depending on the data path you are building.

.. toctree::
   :maxdepth: 1
   :caption: Hardware:

   dma/index

   raw/index
