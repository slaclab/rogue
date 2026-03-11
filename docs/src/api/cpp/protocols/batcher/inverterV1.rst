.. _protocols_batcher_classes_inverterV1:

==========
InverterV1
==========

``InverterV1`` rewrites Batcher v1 framing in place and forwards one
transformed output frame per input frame.
It is not a batching or unbatching stage.
For conceptual guidance, see :doc:`/built_in_modules/protocols/batcher/inverter`.

Protocol reference: https://confluence.slac.stanford.edu/x/th1SDg

Python binding
==============

This C++ class is also exported into Python as ``rogue.protocols.batcher.InverterV1``.

Python API page:
- :doc:`/api/python/rogue/protocols/batcher_inverterv1`

InverterV1 objects in C++ are referenced by the following shared pointer typedef:

.. doxygentypedef:: rogue::protocols::batcher::InverterV1Ptr

The class description is shown below:

.. doxygenclass:: rogue::protocols::batcher::InverterV1
   :members:
