.. _interfaces_memory_master:

======
Master
======

The memory interface Master class is the interface for initiating a memory transaction.
Each Master class object will be coupled with one or more :ref:`interfaces_memory_slave` objects.

The Master class generates log entries with the path: "pyrogue.memory.Master"

Master objects in C++ are referenced by the following shared pointer typedef:

.. doxygentypedef:: rogue::interfaces::memory::MasterPtr

The class description is shown below:

.. doxygenclass:: rogue::interfaces::memory::Master
   :members:

