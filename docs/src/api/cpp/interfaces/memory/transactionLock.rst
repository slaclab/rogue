.. _interfaces_memory_transaction_lock:

===============
TransactionLock
===============

For conceptual transaction lifecycle and lock semantics, see:

- :doc:`/memory_interface/transactions`

TransactionLock objects in C++ are referenced by the following shared pointer typedef:

.. doxygentypedef:: rogue::interfaces::memory::TransactionLockPtr

The class description is shown below:

.. doxygenclass:: rogue::interfaces::memory::TransactionLock
   :members:
