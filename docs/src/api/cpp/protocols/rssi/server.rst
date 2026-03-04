.. _protocols_rssi_classes_server:

======
Server
======

``Server`` is the role-specific convenience wrapper that owns and wires the
RSSI ``Transport``, ``Application``, and ``Controller`` objects for server
operation.


Server objects in C++ are referenced by the following shared pointer typedef:

.. doxygentypedef:: rogue::protocols::rssi::ServerPtr

The class description is shown below:

.. doxygenclass:: rogue::protocols::rssi::Server
   :members:
