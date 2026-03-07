.. _hardware_raw_memory:

======================
Using The MemMap Class
======================

The MemMap class allows you to connect memory masters to local hardware
registers using the /dev/map interface. To avoid uneccessary mapping of
large spaces, each MemMap instance is associated with a specific span of
memory, including a base address and size. In most cases it is better to use
the :ref:`hardware_axi_axi_mem_map` class.

See :ref:`hardware_raw_mem_map` for more information about the MemMap class methods.

Python MemMap Example
=====================

.. code-block:: python

   import pyrogue
   import rogue.hardware

   # Create memory mapped interface
   memMap = rogue.hardware.Memmap(0x00001000, 0x1000)

   # Create a memory master
   memMast = MyMemMaster()

   # Connect memory master to memory map
   memMast >> memMap

C++ AxiMemMap Example
=====================

The equivalent code in C++ is show below:

.. code-block:: c

   #include <rogue/hardware/MemMap.h>

   // Create memory mapped interface
   rogue::hardware::MemMapPtr memMap = rogue::hardware::MemMap::create(0x00001000,0x1000);

   // Create a memory master
   MyMemMasterPtr memMast = MyMemMaster.create();

   // Connect memory master to memory map
   *memMast >> memMap;

