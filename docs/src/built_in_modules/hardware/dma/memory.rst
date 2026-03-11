.. _hardware_axi_memory:

============
AxiMemMap
============

``AxiMemMap`` wraps the ``aes-stream-drivers`` memory access path as a Rogue
Memory interface endpoint. Memory masters can initiate transactions through it
using standard Rogue memory semantics.

The ``AxiMemMap`` class allows you to connect memory masters to PCIe and
Zynq7000-based FPGA firmware that uses the generic AXI stream drivers.
Hardware that uses this pattern includes, but is not limited to:

- PgpCard3 with the AXI stream DMA engine.
- KCU1500.
- Zynq7000 FPGA with TID-AIR RCE firmware.

The example below assumes a single card is being accessed by a single master,
with the master being the device model shown in
:ref:`interfaces_memory_master_ex`.

``AxiMemMap`` processes queued transactions in a worker thread and executes
driver register operations underneath. Transactions are 32-bit word based
(4-byte alignment), matching the class memory-slave configuration and driver
register access model.

Use ``AxiMemMap`` when your firmware exposes register access through the
driver path and you want a direct Rogue Memory endpoint.

Logging
=======

``AxiMemMap`` uses Rogue C++ logging.

- Logger name: ``pyrogue.axi.AxiMemMap``
- Configuration API:
  ``rogue.Logging.setFilter('pyrogue.axi.AxiMemMap', rogue.Logging.Debug)``
- Typical messages: transaction issue/completion flow and transaction timeouts

Set the filter before constructing the ``AxiMemMap`` object.

Python AxiMemMap Example
========================

.. code-block:: python

   import rogue.hardware.axi as rha

   mem_map = rha.AxiMemMap('/dev/datadev_0')
   mem_mast = MyMemMaster()
   mem_mast >> mem_map

C++ AxiMemMap Example
=====================

.. code-block:: cpp

   #include <rogue/hardware/axi/AxiMemMap.h>

   namespace rha = rogue::hardware::axi;

   // Open AXI memory-mapped driver endpoint.
   auto memMap = rha::AxiMemMap::create("/dev/datadev_0");

   // Create an upstream Rogue memory master.
   auto memMast = MyMemMaster::create();

   // Route memory transactions from master into AXI memory map endpoint.
   *memMast >> memMap;

API references
==============

- Python: :doc:`/api/python/hardware_axi_aximemmap`
- C++: :doc:`/api/cpp/hardware/axi/axiMemMap`
