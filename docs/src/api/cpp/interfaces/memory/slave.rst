.. _interfaces_memory_slave:

======
Slave
======

For conceptual guidance on memory-bus roles and transaction handling, see:

- :doc:`/memory_interface/index`
- :doc:`/memory_interface/transactions`

Python binding
--------------

This C++ class is also exported into Python as ``rogue.interfaces.memory.Slave``.

Python API page:
- :doc:`/api/python/rogue/interfaces/memory/slave`

objects in C++ are referenced by the following shared pointer typedef:

.. doxygentypedef:: rogue::interfaces::memory::SlavePtr

The class description is shown below:

.. doxygenclass:: rogue::interfaces::memory::Slave
   :members:
