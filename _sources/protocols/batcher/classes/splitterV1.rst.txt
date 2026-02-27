.. _protocols_batcher_classes_splitterV1:

==========
SplitterV1
==========

``SplitterV1`` decodes a Batcher v1 super-frame and emits one Rogue stream
frame per record.

Protocol reference: https://confluence.slac.stanford.edu/x/th1SDg

SplitterV1 objects in C++ are referenced by the following shared pointer typedef:

.. doxygentypedef:: rogue::protocols::batcher::SplitterV1Ptr

The SplitterV1 class description is shown below:

.. doxygenclass:: rogue::protocols::batcher::SplitterV1
   :members:
