.. _interfaces_simulation_mememulate:

====================
MemEmulate
====================

``MemEmulate`` is a Python ``rogue.interfaces.memory.Slave`` implementation
that stores bytes in a local dictionary-backed address space.

It is useful for testing ``RemoteVariable`` access behavior and retry handling
without requiring hardware.

Behavior and parameters
=======================

Constructor signature:

.. code-block:: python

   sim = pyrogue.interfaces.simulation.MemEmulate(
       minWidth=4,
       maxSize=0xFFFFFFFF,
       dropCount=0,
   )

Parameter effects:

- ``minWidth``: required alignment granularity for transaction addresses
- ``maxSize``: maximum accepted transaction size in bytes
- ``dropCount``: number of transactions intentionally dropped before one is
  accepted; useful for exercising retry logic

Operational notes:

- Write/post transactions copy incoming bytes into emulated memory
- Read/verify transactions return bytes from emulated memory
- Unread addresses default to ``0x00``

Basic usage with a Root
=======================

.. code-block:: python

   import pyrogue as pr
   import pyrogue.interfaces.simulation as pis

   class MyRoot(pr.Root):
       def __init__(self):
           super().__init__(name='MyRoot', timeout=1.0, pollEn=False)

           sim = pis.MemEmulate(minWidth=4, maxSize=0x1000)
           self.addInterface(sim)

           self.add(MyDevice(name='Dev', offset=0x0, memBase=sim))

Retry-test pattern
==================

``dropCount`` can be used to validate variable retry behavior:

.. code-block:: python

   sim = pyrogue.interfaces.simulation.MemEmulate(dropCount=2)
   # With retryCount >= 2 on variables, transient drops can still succeed.

This pattern is exercised in ``tests/test_retry_memory.py``.

Where to explore next
=====================

- Memory interface transaction flow: :doc:`/memory_interface/transactions`
- Device/hub interception patterns: :doc:`/memory_interface/hub`
