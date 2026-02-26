.. _protocols_rssi_classes_controller:

==========
Controller
==========

``Controller`` is the core RSSI protocol engine. It implements handshake/state
transitions, negotiated-parameter management, retransmission behavior, and
flow-control decisions while bridging ``Transport`` and ``Application`` paths.


.. doxygentypedef:: rogue::protocols::rssi::ControllerPtr

.. doxygenclass:: rogue::protocols::rssi::Controller
   :members:
