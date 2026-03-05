.. _interfaces_memory_connecting:

==========================
Connecting Memory Elements
==========================

A memory master and slave are connected using the following commands in python:

.. code-block:: python

   import pyrogue

   # Assume we are creating a memory tree with two masters, masterA and masterB
   # connected to hubA & hubB. We then connect those two hubs to the a SrpV3 gateway.

   # Connect masterA to hubA & hubB to the srpV3 Slave
   masterA >> hubA >> srpV3

   # Connections can also go in the reverse order
   srpV3 << hubB << masterB

   # Alternatively a helper function can be used
   pyrogue.busConnect(masterA, hubA)
   pyrogue.busConnect(hubA, srpV3)

The equivalent code in C++ is show below:

.. code-block:: c

   // Assume we are creating a memory tree with two masters, masterA and masterB
   // connected to hubA & hubB. We then connect those two hubs to the a SrpV3 gateway.

   *( *masterA >> hubA) >> srpV3;

   // Or the reverse
   *( *srpV3 << hubB) << masterB;

   // Alternatively a helper function can be used
   roguebusConnect(masterA, hubA)
   roguebusConnect(hubA, srpV3)
