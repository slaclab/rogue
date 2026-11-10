.. _memory_interface_docs:
.. _interfaces_memory:

================
Memory Interface
================

The Rogue memory interface moves register and memory transactions between
``Master`` and ``Slave`` objects through a composable bus graph.

You usually encounter this layer when building or debugging custom register-bus
topologies, protocol gateways, or address translators. In many PyRogue
applications, the lower-level memory wiring is hidden beneath ``Device`` and
``Root`` abstractions. When those abstractions are not enough, the memory
interface provides the primitives needed to build the bus directly.

At a high level, the memory interface is used to:

- Initiate reads, writes, posted writes, and verify operations
- Route transactions through address windows and translation layers
- Split or transform transactions when a bus topology requires it
- Bridge register access across protocol boundaries such as TCP

Core Types
==========

Four types appear throughout the memory interface:

- ``Master`` initiates transactions
- ``Slave`` services incoming transactions
- ``Hub`` routes, offsets, or splits transactions between bus segments
- ``Transaction`` carries address, type, size, data access, timeout state, and
  completion or error information

Each memory access is represented by a ``Transaction`` object. That
``Transaction`` moves through the bus graph, with ``Hub`` layers adjusting
addresses or generating downstream work as needed before a final ``Slave``
services the request.

Implementation Model
====================

The memory interface implementation lives in C++ for deterministic behavior and
performance. Python bindings expose the same primitives so custom bus graphs can
still be assembled and integrated in Python-based applications.

That split supports a practical workflow:

1. Build and connect the memory graph in Python when exploring a design.
2. Validate addressing, routing, and transaction behavior.
3. Move only the performance-critical or hardware-facing pieces into C++ when
   needed.

Connection Model
================

Memory links use the same operator style as other Rogue connection graphs:

- ``master >> slave`` creates a one-way memory path
- ``slave << master`` creates the same path in reverse syntax
- Python helper: ``pyrogue.busConnect(source, dest)``
- C++ helper: ``rogueBusConnect(source, dest)``

Bus topology is often rooted in one or more protocol or hardware-facing
``Slave`` objects, with ``Hub`` layers and custom memory components organizing
address windows between them.

What To Explore Next
====================

- Bus wiring patterns: :doc:`/memory_interface/connecting`
- Transaction lifecycle details: :doc:`/memory_interface/transactions`
- Custom ``Master`` patterns: :doc:`/memory_interface/master`
- Custom ``Slave`` patterns: :doc:`/memory_interface/slave`
- ``Hub`` translation patterns: :doc:`/memory_interface/hub`
- TCP bridge usage: :doc:`/memory_interface/tcp_bridge`

API Reference
=============

- Python:

  - :doc:`/api/python/rogue/interfaces/memory/master`
  - :doc:`/api/python/rogue/interfaces/memory/slave`
  - :doc:`/api/python/rogue/interfaces/memory/hub`
  - :doc:`/api/python/rogue/interfaces/memory/transaction`

- C++:

  - :doc:`/api/cpp/interfaces/memory/master`
  - :doc:`/api/cpp/interfaces/memory/slave`
  - :doc:`/api/cpp/interfaces/memory/hub`
  - :doc:`/api/cpp/interfaces/memory/transaction`

.. toctree::
   :maxdepth: 1
   :caption: Memory Interface:

   connecting
   master
   slave
   hub
   tcp_bridge
   transactions
