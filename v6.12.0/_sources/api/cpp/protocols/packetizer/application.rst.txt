.. _protocols_packetizer_classes_application:

===========
Application
===========

``Application`` is the per-destination packetizer endpoint used by upper-layer
protocol/application stream paths.
This page is reference-only; for conceptual context see
:doc:`/built_in_modules/protocols/packetizer/index`.


Python binding
--------------

This C++ class is also exported into Python as ``rogue.protocols.packetizer.Application``.

Python API page:
- :doc:`/api/python/rogue/protocols/packetizer/application`

objects in C++ are referenced by the following shared pointer typedef:

.. doxygentypedef:: rogue::protocols::packetizer::ApplicationPtr

The class description is shown below:

.. doxygenclass:: rogue::protocols::packetizer::Application
   :members:
