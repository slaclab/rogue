.. _interfaces_memory_transaction:

===========
Transaction
===========

For conceptual guidance on transaction flow, timeout behavior, and
subtransactions, see :doc:`/memory_interface/transactions`.


Transaction objects in C++ are referenced by the following shared pointer typedef:

.. doxygentypedef:: rogue::interfaces::memory::TransactionPtr

The class description is shown below:

.. doxygenclass:: rogue::interfaces::memory::Transaction
   :members:
