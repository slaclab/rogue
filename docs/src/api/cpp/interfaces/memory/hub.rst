.. _interfaces_memory_hub:

===
Hub
===

For conceptual guidance on address translation and transaction fan-out, see:

- :doc:`/memory_interface/transactions`
- :doc:`/memory_interface/index`

Python binding
--------------

This C++ class is also exported into Python as ``rogue.interfaces.memory.Hub``.

Python API page:
- :doc:`/api/python/interfaces_memory_hub`

objects in C++ are referenced by the following shared pointer typedef:

.. doxygentypedef:: rogue::interfaces::memory::HubPtr

The class description is shown below:

.. doxygenclass:: rogue::interfaces::memory::Hub
   :members:
