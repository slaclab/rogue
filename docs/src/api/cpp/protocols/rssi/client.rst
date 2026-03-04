.. _protocols_rssi_classes_client:

======
Client
======

``Client`` is the role-specific convenience wrapper that owns and wires the
RSSI ``Transport``, ``Application``, and ``Controller`` objects for client
operation.


Client objects in C++ are referenced by the following shared pointer typedef:

.. doxygentypedef:: rogue::protocols::rssi::ClientPtr

The class description is shown below:

.. doxygenclass:: rogue::protocols::rssi::Client
   :members:
