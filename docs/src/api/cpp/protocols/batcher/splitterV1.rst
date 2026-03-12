.. _protocols_batcher_classes_splitterV1:

==========
SplitterV1
==========

``SplitterV1`` decodes a Batcher v1 super-frame and emits one Rogue stream
frame per record.
For conceptual guidance, see :doc:`/built_in_modules/protocols/batcher/splitter`.

Protocol reference: https://confluence.slac.stanford.edu/x/th1SDg

Python binding
==============

This C++ class is also exported into Python as ``rogue.protocols.batcher.SplitterV1``.

Python API page:
- :doc:`/api/python/rogue/protocols/batcher/splitterv1`

SplitterV1 objects in C++ are referenced by the following shared pointer typedef:

.. doxygentypedef:: rogue::protocols::batcher::SplitterV1Ptr

The class description is shown below:

.. doxygenclass:: rogue::protocols::batcher::SplitterV1
   :members:
