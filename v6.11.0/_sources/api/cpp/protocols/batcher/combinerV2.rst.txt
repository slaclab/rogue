.. _protocols_batcher_classes_combinerV2:

==========
CombinerV2
==========

``CombinerV2`` combines individual Rogue stream frames into a Batcher v2
super-frame. It is the software inverse of ``SplitterV2``.
For conceptual guidance, see :doc:`/built_in_modules/protocols/batcher/combiner`.

Protocol reference: https://confluence.slac.stanford.edu/x/L2VlK

Python binding
==============

This C++ class is also exported into Python as ``rogue.protocols.batcher.CombinerV2``.

Python API page:
- :doc:`/api/python/rogue/protocols/batcher/combinerv2`

CombinerV2 objects in C++ are referenced by the following shared pointer typedef:

.. doxygentypedef:: rogue::protocols::batcher::CombinerV2Ptr

The class description is shown below:

.. doxygenclass:: rogue::protocols::batcher::CombinerV2
   :members:
