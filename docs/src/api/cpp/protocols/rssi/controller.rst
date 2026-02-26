.. _protocols_rssi_classes_controller:

==========
Controller
==========

.. note::
   Canonical generated C++ API docs are centralized at :ref:`api_reference`.



``Controller`` is the core RSSI protocol engine. It implements handshake/state
transitions, negotiated-parameter management, retransmission behavior, and
flow-control decisions while bridging ``Transport`` and ``Application`` paths.


