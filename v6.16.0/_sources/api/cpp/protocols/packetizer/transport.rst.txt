.. _protocols_packetizer_classes_transport:

=========
Transport
=========

``Transport`` is the lower packetizer endpoint that bridges packetizer frames
to and from the underlying stream transport.
This page is reference-only; for conceptual context see
:doc:`/built_in_modules/protocols/packetizer/index`.


Python binding
--------------

This C++ class is also exported into Python as ``rogue.protocols.packetizer.Transport``.

Python API page:
- :doc:`/api/python/rogue/protocols/packetizer/transport`

objects in C++ are referenced by the following shared pointer typedef:

.. doxygentypedef:: rogue::protocols::packetizer::TransportPtr

The class description is shown below:

.. doxygenclass:: rogue::protocols::packetizer::Transport
   :members:
