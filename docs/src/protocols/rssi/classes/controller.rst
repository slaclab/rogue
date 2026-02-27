.. _protocols_rssi_classes_controller:

==========
Controller
==========

``Controller`` is the core RSSI protocol engine. It implements handshake/state
transitions, negotiated-parameter management, retransmission behavior, and
flow-control decisions while bridging ``Transport`` and ``Application`` paths.

Controller objects in C++ are referenced by the following shared pointer typedef:

.. doxygentypedef:: rogue::protocols::rssi::ControllerPtr

The Controller class description is shown below:

.. doxygenclass:: rogue::protocols::rssi::Controller
   :members:
