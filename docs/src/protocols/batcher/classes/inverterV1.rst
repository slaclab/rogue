.. _protocols_batcher_classes_inverterV1:

==========
InverterV1
==========

``InverterV1`` rewrites Batcher v1 framing in place and forwards one
transformed output frame per input frame.
It is not a batching or unbatching stage.

Protocol reference: https://confluence.slac.stanford.edu/x/th1SDg

InverterV1 objects in C++ are referenced by the following shared pointer typedef:

.. doxygentypedef:: rogue::protocols::batcher::InverterV1Ptr

The InverterV1 class description is shown below:

.. doxygenclass:: rogue::protocols::batcher::InverterV1
   :members:
