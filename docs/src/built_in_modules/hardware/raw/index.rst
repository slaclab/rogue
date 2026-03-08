.. _hardware_raw:
.. _hardware_raw_memory:

======================
Raw Hardware Interface
======================

The raw hardware path provides direct memory mapping through ``/dev/mem`` style
interfaces. It is useful for tightly scoped local register windows, but most
systems should prefer :doc:`/built_in_modules/hardware/axi/index` when AXI
driver support is available.

C++ API details for raw hardware interfaces are documented in
:doc:`/api/cpp/hardware/raw/index`.

Using The MemMap Class
======================

The ``MemMap`` class maps a specific base address and size. Keeping each
instance constrained to the smallest required span avoids unnecessary mapping
of large address spaces.

Python MemMap Example
=====================

.. code-block:: python

   import rogue.hardware as rh

   mem_map = rh.MemMap(0x00001000, 0x1000)
   mem_mast = MyMemMaster()
   mem_mast >> mem_map

C++ MemMap Example
==================

.. code-block:: cpp

   #include <rogue/hardware/MemMap.h>

   namespace rh = rogue::hardware;

   auto memMap = rh::MemMap::create(0x00001000, 0x1000);
   auto memMast = MyMemMaster::create();
   *memMast >> memMap;
