.. _interfaces_memory_block:

=====
Block
=====

For conceptual guidance on block behavior and variable-to-transaction mapping,
see:

- :ref:`pyrogue_tree_node_block`
- :doc:`/memory_interface/index`


Python binding
--------------

This C++ class is also exported into Python as ``rogue.interfaces.memory.Block``.

Python API page:
- :doc:`/api/python/rogue/interfaces/memory/block`

objects in C++ are referenced by the following shared pointer typedef:

.. doxygentypedef:: rogue::interfaces::memory::BlockPtr

The class description is shown below:

.. doxygenclass:: rogue::interfaces::memory::Block
   :members:
