.. _hardware_axi_memory:

=========================
Using The AxiMemMap Class
=========================

The AxiMemMap class allows you to connect memory masters to PCI-Express and
Zynq7000 based FPGA firmware which utilize the generic AXI Stream drivers. 
The set of hardware which use this include but are not limited to:

- PgpCard3 with the AXI Stream DMA engine
- KCU1500 board
- Zynq7000 FPGA with TID-AIRs RCe core firmware

The following example assumes a single card is being accessed by a single master,
with the master being the device created in the :ref:`interfaces_memory_master_ex`.

See :ref:`hardware_axi_axi_mem_map` for more information about the AxiMemMap class methods.

Python AxiMemMap Example
========================

.. code-block:: python

   import pyrogue
   import rogue.hardware.axi

   # Create memory mapped AXI interface
   memMap = rogue.hardware.axi.AxiMemmap('/dev/datadev_0')

   # Create a memory master
   memMast = MyMemMaster()

   # Connect memory master to memory map
   memMast >> memMap

C++ AxiMemMap Example
=====================

The equivalent code in C++ is show below:

.. code-block:: c

   #include <rogue/hardware/axi/AxiMemMap.h>

   // Create memory mapped AXI interface
   rogue::hardware::axi::AxiMemMapPtr memMap = rogue::hardware::axi::AxiMemMap::create("/dev/datadev_0");

   // Create a memory master
   MyMemMasterPtr memMast = MyMemMaster.create();

   // Connect memory master to memory map
   *memMast >> memMap;

