.. _protocols_batcher_classes_inverterV2:

==========
InverterV2
==========

``InverterV2`` rewrites Batcher v2 framing in place and forwards one
transformed output frame per input frame.
It is not a batching or unbatching stage.

Protocol reference: https://confluence.slac.stanford.edu/x/L2VlK


InverterV2 objects in C++ are referenced by the following shared pointer typedef:

.. doxygentypedef:: rogue::protocols::batcher::InverterV2Ptr

The class description is shown below:

.. doxygenclass:: rogue::protocols::batcher::InverterV2
   :members:
