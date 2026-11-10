.. _interfaces_memory_connecting:
.. _memory_interface_connecting:

==========================
Connecting Memory Elements
==========================

A memory bus is built by connecting a transaction source, usually a ``Master``,
to a transaction sink, usually a ``Slave``, optionally through one or more
``Hub`` layers.

You typically connect memory elements when assembling an address map from
several components. Common cases include attaching multiple upstream initiators
to a shared protocol endpoint, inserting a ``Hub`` that translates address
windows, or connecting a custom bus component to a hardware-facing or
network-facing ``Slave``.

At a high level, the bus topology usually looks like this:

1. Upstream ``Master`` objects issue transactions.
2. ``Hub`` layers apply routing, offset, or splitting behavior.
3. A protocol or hardware-facing ``Slave`` services the final transaction.

Operator Syntax And Helpers
===========================

Python
------

.. code-block:: python

   import pyrogue as pr

   # Build a tree with two upstream Masters feeding two Hubs and then a
   # protocol-facing Slave.
   master_a >> hub_a >> srp
   srp << hub_b << master_b

   # Equivalent helper style
   pr.busConnect(master_a, hub_a)
   pr.busConnect(hub_a, srp)

The operator form is concise and reads naturally once the topology is familiar.
The helper form is useful when code style or readability favors explicit calls.

C++
---

.. code-block:: cpp

   #include "rogue/Helpers.h"

   // Build a tree with two upstream Masters feeding two Hubs and then a
   // protocol-facing Slave.
   *(*masterA >> hubA) >> srp;
   *(*srp << hubB) << masterB;

   // Equivalent helper style
   rogueBusConnect(masterA, hubA);
   rogueBusConnect(hubA, srp);

Addressing Model
================

One of the main jobs of a memory bus is to let each layer expose a clean local
address window while still reaching the correct downstream absolute address.
``Hub`` and device layers often present relative upstream address spaces and map
them to different downstream base offsets.

That means the bus can be organized in terms of logical subregions while still
arriving at the correct physical register addresses underneath.

What To Explore Next
====================

- Custom ``Master`` patterns: :doc:`/memory_interface/master`
- Custom ``Slave`` patterns: :doc:`/memory_interface/slave`
- ``Hub`` translation patterns: :doc:`/memory_interface/hub`
- Transaction lifecycle details: :doc:`/memory_interface/transactions`

API Reference
=============

- Python:

  - :doc:`/api/python/rogue/interfaces/memory/master`
  - :doc:`/api/python/rogue/interfaces/memory/hub`
  - :doc:`/api/python/rogue/interfaces/memory/slave`

- C++:

  - :doc:`/api/cpp/interfaces/memory/master`
  - :doc:`/api/cpp/interfaces/memory/hub`
  - :doc:`/api/cpp/interfaces/memory/slave`
