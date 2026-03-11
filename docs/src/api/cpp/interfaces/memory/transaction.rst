.. _interfaces_memory_transaction:

===========
Transaction
===========

For conceptual guidance on transaction flow, timeout behavior, and
subtransactions, see :doc:`/memory_interface/transactions`.


Python binding
--------------

This C++ class is also exported into Python as ``rogue.interfaces.memory.Transaction``.

Python API page:
- :doc:`/api/python/rogue/interfaces/memory/transaction`

objects in C++ are referenced by the following shared pointer typedef:

.. doxygentypedef:: rogue::interfaces::memory::TransactionPtr

The class description is shown below:

.. doxygenclass:: rogue::interfaces::memory::Transaction
   :members:
