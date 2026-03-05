.. _protocols_rssi_classes_server:

======
Server
======

``Server`` is the role-specific convenience wrapper that owns and wires the
RSSI ``Transport``, ``Application``, and ``Controller`` objects for server
operation.

Threading and Lifecycle
=======================

- Delegates protocol-state execution to ``Controller`` and does not create a
  dedicated ``Server`` worker thread.
- Implements Managed Interface Lifecycle:
  :ref:`pyrogue_tree_node_device_managed_interfaces`


Server objects in C++ are referenced by the following shared pointer typedef:

.. doxygentypedef:: rogue::protocols::rssi::ServerPtr

The class description is shown below:

.. doxygenclass:: rogue::protocols::rssi::Server
   :members:
