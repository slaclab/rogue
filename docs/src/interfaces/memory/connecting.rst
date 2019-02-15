.. _interfaces_memory_connecting:

==========================
Connecting Memory Elements
==========================

A memory master and slave are connected using the following commands in python:

.. code-block:: python

   import pyrogue

   # Assume we are crated a memory tree with two masters, masterA and masterB 
   # connected to hubA. We then have hubA and an additional masterC, connected
   # the a SrpV3 gateway.

   # Connect masterA and masterB to hubA
   pyrogue.busConnect(masterA, hubA)
   pyrogue.busConnect(masterB, hubA)

   # Connect hubA and masterC to the srpV3 Slave
   pyrogue.busConnect(hubA, srpv3)
   pyrogue.busConnect(masterC, srpv3)


The equivelent code in C++ is show below:

.. code-block:: c

   #include <rogue/Helpers.h>

   // Assume we are crated a memory tree with two masters, masterA and masterB 
   // connected to hubA. We then have hubA and an additional masterC, connected
   // the a SrpV3 gateway.

   // Connect masterA and masterB to hubA
   busConnect(masterA, hubA)
   busConnect(masterB, hubA)

   // Connect hubA and masterC to the srpV3 Slave
   busConnect(hubA, srpv3)
   busConnect(masterC, srpv3)

