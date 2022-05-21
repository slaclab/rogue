.. _interfaces_memory_block:

=====
Block
=====

The memory interface Block class provides a mirror for the hardware register space as well as serving as a translater between python types and hardware bits and bytes.

Block objects in C++ are referenced by the following shared pointer typedef:

.. doxygentypedef:: rogue::interfaces::memory::BlockPtr

The class description is shown below:

.. doxygenclass:: rogue::interfaces::memory::Block
   :members:

