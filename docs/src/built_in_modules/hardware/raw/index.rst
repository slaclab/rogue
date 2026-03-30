.. _hardware_raw:
.. _hardware_raw_memory:

======================
Raw Hardware Interface
======================

For direct local mapping of a physical register window through ``/dev/mem``,
Rogue provides ``rogue.hardware.MemMap``.

This is the minimal hardware access path. It is useful when a platform exposes a
small host-visible register span and no DMA-driver wrapper is available, but it
is not the normal choice for PCIe or DMA-backed systems. When
``aes-stream-drivers`` support exists, :doc:`/built_in_modules/hardware/dma/index`
is usually the better integration path.

Use Cases
=========

- A simple local register window.
- Early bring-up or tightly scoped platform utilities.
- Systems without the standard DMA driver stack.

Key Constructor Arguments
=========================

``MemMap(base, size)``

- ``base`` is the physical base address to map
- ``size`` is the number of bytes to expose

How It Works
============

``MemMap`` maps the requested physical range and services queued Rogue memory
transactions against that mapped window. Transactions are interpreted relative
to the mapped base address.

Root-Based Example
==================

When ``MemMap`` is used in a PyRogue application, it is usually created in the
``Root`` and passed as ``memBase`` to an existing device class.

.. code-block:: python

   import pyrogue as pr
   import pyrogue.examples
   import rogue.hardware as rh

   class LocalRoot(pr.Root):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)

           # Map a 4 KB register window starting at physical address 0x1000.
           self.memMap = rh.MemMap(0x00001000, 0x1000)
           self.addInterface(self.memMap)

           # Attach an existing example device to the mapped register space.
           self.add(pyrogue.examples.AxiVersion(
               memBase=self.memMap,
               name='AxiVersion',
               offset=0x00000000,
               expand=True,
           ))

Standalone Memory-Master Example
================================

If you are not building a PyRogue tree, ``MemMap`` can still be used as a plain
Rogue memory endpoint:

.. code-block:: python

   import rogue.hardware as rh

   # Map a 0x1000-byte register window starting at address 0x00001000.
   mem_map = rh.MemMap(0x00001000, 0x1000)
   mem_master >> mem_map

Threading And Lifecycle
=======================

``MemMap`` does create a background worker thread:

- ``doTransaction()`` enqueues requests from upstream.
- The worker thread performs mapped-memory accesses.
- Destruction or ``_stop()`` shuts down the worker, unmaps the region, and
  closes ``/dev/mem``.

Operational Notes
=================

Keep the mapped span as small as practical. Use this path only when direct
``/dev/mem`` access is appropriate for the target system. When a driver-backed
integration already exists, the AXI DMA wrappers are usually the better choice.

Logging
=======

``MemMap`` uses Rogue C++ logging:

- Logger name: ``pyrogue.MemMap``
- Unified Logging API:
  ``pyrogue.setLogLevel('pyrogue.MemMap', 'DEBUG')``
- Legacy Logging API:
  ``rogue.Logging.setFilter('pyrogue.MemMap', rogue.Logging.Debug)``
- Typical messages: mapped-range creation, issued transactions, and transaction
  timeout warnings

You can enable it before or after construction. Enable it before construction
only if you want constructor or initial startup messages:

.. code-block:: python

   import rogue

   rogue.Logging.setFilter('pyrogue.MemMap', rogue.Logging.Debug)

Related Topics
==============

- :doc:`/built_in_modules/hardware/dma/index`
- :doc:`/memory_interface/index`

API Reference
=============

- Python: :doc:`/api/python/rogue/hardware/memmap`
- C++: :doc:`/api/cpp/hardware/raw/memMap`
