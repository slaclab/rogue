.. _protocols_packetizer_classes_controller:

==========
Controller
==========

``Controller`` is the shared packetizer base controller that routes traffic
between one transport endpoint and multiple application endpoints.
Concrete protocol behavior is provided by ``ControllerV1`` and ``ControllerV2``.
This page is reference-only; for conceptual context see
:doc:`/protocols/packetizer/index`.


Controller objects in C++ are referenced by the following shared pointer typedef:

.. doxygentypedef:: rogue::protocols::packetizer::ControllerPtr

The class description is shown below:

.. doxygenclass:: rogue::protocols::packetizer::Controller
   :members:
