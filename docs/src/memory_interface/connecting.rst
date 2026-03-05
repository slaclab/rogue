.. _interfaces_memory_connecting:
.. _memory_interface_connecting:

==========================
Connecting Memory Elements
==========================

A memory bus is built by connecting a transaction source (``Master``) to a
transaction sink (``Slave``), optionally through one or more ``Hub`` layers.

Operator syntax and helpers
===========================

Python
------

.. code-block:: python

   import pyrogue as pr

   master_a >> hub_a >> srp
   srp << hub_b << master_b

   # Equivalent helper style
   pr.busConnect(master_a, hub_a)
   pr.busConnect(hub_a, srp)

C++
---

.. code-block:: cpp

   #include "rogue/Helpers.h"

   *(*masterA >> hubA) >> srp;
   *(*srp << hubB) << masterB;

   // Equivalent helper style
   rogueBusConnect(masterA, hubA);
   rogueBusConnect(hubA, srp);

Topology pattern
================

A common pattern is:

1. Upstream masters issue requests.
2. Hubs apply offset/routing/splitting.
3. A protocol or hardware-facing slave services the transaction.

Addressing note
===============

Hub/device layers usually expose relative upstream windows while mapping to
absolute downstream addresses through configured base offsets.

What to explore next
====================

- Custom transaction initiators: :doc:`/memory_interface/master`
- Custom transaction responders: :doc:`/memory_interface/slave`
- Bus translation hubs: :doc:`/memory_interface/hub`
