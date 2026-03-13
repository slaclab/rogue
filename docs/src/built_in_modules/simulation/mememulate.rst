.. _interfaces_simulation_mememulate:

====================
MemEmulate
====================

``MemEmulate`` is a Python ``rogue.interfaces.memory.Slave`` implementation
that stores bytes in a local dictionary-backed address space.

It is useful for testing ``RemoteVariable`` access behavior and retry handling
without requiring hardware.

Configuration Example
=====================

.. code-block:: python

   import pyrogue.interfaces.simulation as pis

   sim = pis.MemEmulate(
       minWidth=4,
       maxSize=0xFFFFFFFF,
       dropCount=0,
   )

Key Constructor Arguments
=========================

- ``minWidth``: required alignment granularity for transaction addresses
- ``maxSize``: maximum accepted transaction size in bytes
- ``dropCount``: number of transactions intentionally dropped before one is
  accepted; useful for exercising retry logic

Operational Notes
=================

- Write/post transactions copy incoming bytes into emulated memory
- Read/verify transactions return bytes from emulated memory
- Unread addresses default to ``0x00``

The implementation also enforces
alignment against ``minWidth`` and rejects transactions larger than
``maxSize``.

When To Use MemEmulate
======================

Use ``MemEmulate`` when you need deterministic memory behavior during software
integration and want to isolate tree/protocol logic from hardware timing and
transport effects.

Basic Usage with a Root
=======================

.. code-block:: python

   import pyrogue as pr
   import pyrogue.interfaces.simulation as pis

   class MyRoot(pr.Root):
       def __init__(self):
           super().__init__(name='MyRoot', timeout=1.0, pollEn=False)

           # Create emulated memory endpoint.
           sim = pis.MemEmulate(minWidth=4, maxSize=0x1000)
           self.addInterface(sim)

           # Attach a Device so RemoteVariables transact through emulated memory.
           self.add(MyDevice(name='Dev', offset=0x0, memBase=sim))

Retry-Test Pattern
==================

``dropCount`` can be used to validate variable retry behavior:

.. code-block:: python

   import pyrogue.interfaces.simulation as pis

   sim = pis.MemEmulate(dropCount=2)
   # With retryCount >= 2 on variables, transient drops can still succeed.

Related Topics
==============

- Memory interface transaction flow: :doc:`/memory_interface/transactions`
- Device/hub interception patterns: :doc:`/memory_interface/hub`

API Reference
=============

- Python:

  - :doc:`/api/python/pyrogue/interfaces/simulation/mememulate`
  - :doc:`/api/python/rogue/interfaces/memory/slave`
