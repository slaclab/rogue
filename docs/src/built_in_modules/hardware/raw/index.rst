.. _hardware_raw:
.. _hardware_raw_memory:

======================
Raw Hardware Interface
======================

The raw hardware path provides direct memory mapping through ``/dev/mem`` style
interfaces. It is useful for tightly scoped local register windows, but most
systems should prefer :doc:`/built_in_modules/hardware/dma/index` when AXI
driver support is available.

Raw mapping is most appropriate when:

- You need direct access to a fixed host-visible register span.
- A DMA-driver wrapper is not available for the platform.
- The integration is local and intentionally minimal.

Compared to DMA wrappers, raw mapping typically provides less transport
abstraction and fewer hardware-integration conveniences, but a straightforward
memory endpoint for simple register windows.

C++ API details for raw hardware interfaces are documented in
:doc:`/api/cpp/hardware/raw/index`.

Using The MemMap Class
======================

The ``MemMap`` class maps a specific base address and size. Keeping each
instance constrained to the smallest required span avoids unnecessary mapping
of large address spaces.

Parameter overview:

- ``base``: Start address of the mapped region.
- ``size``: Number of bytes to expose through the memory endpoint.

Transactions presented to this endpoint are interpreted relative to the mapped
base, so sizing and alignment choices should match the target register map.

Logging
=======

``MemMap`` uses Rogue C++ logging.

- Logger name: ``pyrogue.MemMap``
- Unified Logging API:
  ``logging.getLogger('pyrogue.MemMap').setLevel(logging.DEBUG)``
- Legacy Logging API:
  ``rogue.Logging.setFilter('pyrogue.MemMap', rogue.Logging.Debug)``
- Typical messages: mapped-range creation, issued transactions, and transaction
  timeout warnings

Python MemMap Example
=====================

.. code-block:: python

   import rogue.hardware as rh

   # Map a 0x1000-byte register window starting at address 0x00001000.
   mem_map = rh.MemMap(0x00001000, 0x1000)

   # Upstream memory master that initiates reads/writes.
   mem_mast = MyMemMaster()

   # Route master transactions into the mapped hardware window.
   mem_mast >> mem_map

C++ MemMap Example
==================

.. code-block:: cpp

   #include <rogue/hardware/MemMap.h>

   namespace rh = rogue::hardware;

   // Map a 0x1000-byte register window starting at address 0x00001000.
   auto memMap = rh::MemMap::create(0x00001000, 0x1000);

   // Upstream memory master that initiates reads/writes.
   auto memMast = MyMemMaster::create();

   // Route master transactions into the mapped hardware window.
   *memMast >> memMap;

Related References
==================

- :doc:`/api/cpp/hardware/raw/memMap`
- :doc:`/memory_interface/index`
