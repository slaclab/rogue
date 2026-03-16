.. _hardware_axi_memory:

=========
AxiMemMap
=========

For register and memory transactions through the ``aes-stream-drivers`` path,
Rogue provides ``rogue.hardware.axi.AxiMemMap``. This class adapts the driver
register-access API into a Rogue memory slave.

Use ``AxiMemMap`` when firmware exposes a memory-mapped register path through
the driver and you want upstream Rogue memory masters or a PyRogue tree to use
normal Rogue memory transactions.

Key Constructor Arguments
=========================

``AxiMemMap(path)``

- ``path`` is the Linux device path, commonly ``/dev/datadev_0``.

How It Works
============

``AxiMemMap`` queues incoming memory transactions, then a worker thread performs
the underlying driver register operations. Transactions are 32-bit word based,
matching the class memory-slave configuration and the driver access model.

Root-Based Example
==================

In PyRogue applications, ``AxiMemMap`` is usually created in the ``Root`` and
then passed as ``memBase`` to the top-level hardware device tree.

.. code-block:: python

   import pyrogue as pr
   import rogue.hardware.axi as rha
   import axipcie

   class BoardRoot(pr.Root):
       def __init__(self, dev='/dev/datadev_0', **kwargs):
           super().__init__(**kwargs)

           self.memMap = rha.AxiMemMap(dev)
           self.addInterface(self.memMap)

           self.add(axipcie.AxiPcieCore(
               memBase=self.memMap,
               offset=0x00000000,
               expand=True,
           ))

Standalone Memory-Master Example
================================

If you are not building a PyRogue tree, ``AxiMemMap`` can still be used as a
plain Rogue memory endpoint:

.. code-block:: python

   import rogue.hardware.axi as rha

   mem_map = rha.AxiMemMap('/dev/datadev_0')
   mem_master >> mem_map

Threading And Lifecycle
=======================

``AxiMemMap`` does create a background worker thread:

- ``doTransaction()`` enqueues requests from upstream.
- The worker thread performs the register access.
- Destruction or ``_stop()`` shuts down the worker and closes the device.

If this object is Root-managed, let the Root control lifecycle. In standalone
use, explicitly stop it when finished.

Logging
=======

``AxiMemMap`` uses Rogue C++ logging:

- Logger name: ``pyrogue.axi.AxiMemMap``
- Unified Logging API:
  ``logging.getLogger('pyrogue.axi.AxiMemMap').setLevel(logging.DEBUG)``
- Legacy Logging API:
  ``rogue.Logging.setFilter('pyrogue.axi.AxiMemMap', rogue.Logging.Debug)``
- Typical messages: transaction issue/completion flow and transaction timeouts

Enable it before construction:

.. code-block:: python

   import rogue

   rogue.Logging.setFilter('pyrogue.axi.AxiMemMap', rogue.Logging.Debug)

Related Topics
==============

- :doc:`/built_in_modules/hardware/dma/index`
- :doc:`/memory_interface/index`

API Reference
=============

- Python: :doc:`/api/python/rogue/hardware/axi/aximemmap`
- C++: :doc:`/api/cpp/hardware/axi/axiMemMap`
