.. _protocols_batcher_classes_splitterV2:

==========
SplitterV2
==========

``SplitterV2`` decodes a Batcher v2 super-frame and emits one Rogue stream
frame per record.

Protocol reference: https://confluence.slac.stanford.edu/x/L2VlK

SplitterV2 objects in C++ are referenced by the following shared pointer typedef:

.. doxygentypedef:: rogue::protocols::batcher::SplitterV2Ptr

The SplitterV2 class description is shown below:

.. doxygenclass:: rogue::protocols::batcher::SplitterV2
   :members:
