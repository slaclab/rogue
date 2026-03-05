.. _protocols_packetizer_classes_core:

====
Core
====

``Core`` is the packetizer v1 wiring object that owns the transport endpoint,
controller, and destination-indexed application endpoints.
This page is reference-only; for integration guidance see
:doc:`/protocols/packetizer/core`.


Core objects in C++ are referenced by the following shared pointer typedef:

.. doxygentypedef:: rogue::protocols::packetizer::CorePtr

The class description is shown below:

.. doxygenclass:: rogue::protocols::packetizer::Core
   :members:
