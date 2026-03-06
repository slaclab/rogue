.. _memory_interface_docs:
.. _interfaces_memory:

================
Memory Interface
================

The Rogue memory interface moves register and memory transactions between
masters and slaves through a composable bus graph.

In typical PyRogue use, most direct memory wiring is handled under ``Device``
and ``Root`` abstractions. When needed, the lower-level memory interfaces let
you build custom bus topologies, protocol bridges, and translation layers.

Core objects
============

- ``Master``: initiates transactions (read, write, post, verify).
- ``Slave``: services incoming transactions.
- ``Hub``: routes/offsets/splits transactions between upstream and downstream
  segments.
- ``Transaction``: carries address, type, size, data access, completion/error
  state, and timeout tracking.

Implementation model
====================

The memory interface implementation is in C++ for deterministic behavior and
performance. Python bindings expose the same primitives for integration and
customization in PyRogue applications.

Class-by-class C++ API details are in
:doc:`/api/cpp/interfaces/memory/index`.

Connection model
================

Memory links use stream-like operators and helper functions:

- ``master >> slave`` / ``slave << master``
- Python helper: ``pyrogue.busConnect(source, dest)``
- C++ helper macro: ``rogueBusConnect(source, dest)``

Bus topology is usually rooted in one or more protocol/gateway slaves (for
example SRP or TCP bridges), with hubs and devices organizing address windows.

Where to go next
================

- Bus wiring patterns: :doc:`/memory_interface/connecting`
- Transaction lifecycle details: :doc:`/memory_interface/transactions`
- Custom master patterns: :doc:`/memory_interface/master`
- Custom slave patterns: :doc:`/memory_interface/slave`
- Hub translation patterns: :doc:`/memory_interface/hub`
- TCP bridge usage: :doc:`/memory_interface/tcp_bridge`


.. toctree::
   :maxdepth: 1
   :caption: Memory Interface:

   connecting
   master
   slave
   hub
   tcp_bridge
   transactions
