.. _protocols_batcher_classes_splitterV2:

==========
SplitterV2
==========

``SplitterV2`` decodes a Batcher v2 super-frame and emits one Rogue stream
frame per record.
For conceptual guidance, see :doc:`/built_in_modules/protocols/batcher/splitter`.

Protocol reference: https://confluence.slac.stanford.edu/x/L2VlK

Python binding
==============

This C++ class is also exported into Python as ``rogue.protocols.batcher.SplitterV2``.

Python API page:
- :doc:`/api/python/rogue/protocols/batcher_splitterv2`

SplitterV2 objects in C++ are referenced by the following shared pointer typedef:

.. doxygentypedef:: rogue::protocols::batcher::SplitterV2Ptr

The class description is shown below:

.. doxygenclass:: rogue::protocols::batcher::SplitterV2
   :members:
