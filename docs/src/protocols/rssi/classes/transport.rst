.. _protocols_rssi_classes_transport:

=========
Transport
=========

``Transport`` is the lower RSSI stream endpoint. It exchanges RSSI frames
between the controller and the underlying link transport.

Transport objects in C++ are referenced by the following shared pointer typedef:

.. doxygentypedef:: rogue::protocols::rssi::TransportPtr

The Transport class description is shown below:

.. doxygenclass:: rogue::protocols::rssi::Transport
   :members:
