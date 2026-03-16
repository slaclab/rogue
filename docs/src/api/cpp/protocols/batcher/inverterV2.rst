.. _protocols_batcher_classes_inverterV2:

==========
InverterV2
==========

``InverterV2`` rewrites Batcher v2 framing in place and forwards one
transformed output frame per input frame.
It is not a batching or unbatching stage.
For conceptual guidance, see :doc:`/built_in_modules/protocols/batcher/inverter`.

Protocol reference: https://confluence.slac.stanford.edu/x/L2VlK

Python binding
==============

This C++ class is also exported into Python as ``rogue.protocols.batcher.InverterV2``.

Python API page:
- :doc:`/api/python/rogue/protocols/batcher/inverterv2`

InverterV2 objects in C++ are referenced by the following shared pointer typedef:

.. doxygentypedef:: rogue::protocols::batcher::InverterV2Ptr

The class description is shown below:

.. doxygenclass:: rogue::protocols::batcher::InverterV2
   :members:
