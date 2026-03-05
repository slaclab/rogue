.. _protocols_packetizer_classes_transport:

=========
Transport
=========

``Transport`` is the lower packetizer endpoint that bridges packetizer frames
to and from the underlying stream transport.
This page is reference-only; for conceptual context see
:doc:`/protocols/packetizer/index`.


Transport objects in C++ are referenced by the following shared pointer typedef:

.. doxygentypedef:: rogue::protocols::packetizer::TransportPtr

The class description is shown below:

.. doxygenclass:: rogue::protocols::packetizer::Transport
   :members:
