.. _protocols_batcher_classes_combinerV1:

==========
CombinerV1
==========

``CombinerV1`` combines individual Rogue stream frames into a Batcher v1
super-frame. It is the software inverse of ``SplitterV1``.
For conceptual guidance, see :doc:`/built_in_modules/protocols/batcher/combiner`.

Protocol reference: https://confluence.slac.stanford.edu/x/th1SDg

Python binding
==============

This C++ class is also exported into Python as ``rogue.protocols.batcher.CombinerV1``.

Python API page:
- :doc:`/api/python/rogue/protocols/batcher/combinerv1`

CombinerV1 objects in C++ are referenced by the following shared pointer typedef:

.. doxygentypedef:: rogue::protocols::batcher::CombinerV1Ptr

The class description is shown below:

.. doxygenclass:: rogue::protocols::batcher::CombinerV1
   :members:
