.. _interfaces_memory:

================
Memory Interface
================

The Rogue Memory Interface provides a mechanism for interfacing with hardware register
space, providing mechanisms for reading and writing these memory spaces while
keeping a local mirror of the current register sets. Address spaces can be created organically
by linking multiple memory masters to memory hubs, with the eventual connection to a memory
slave which serves as the interface to the hardware device.

Each memory access is associated with a transaction object which is used to describe and track all
in progress memory accesses. Transactions are then forwarded through the layers of the memory
bus, with the address being adjusted appropriately based upon its connection at a Hub. The Hub
may forward the transaction onward, but also has the ability to conver the single transaction
into multiple downstream transactions, providing a mechanism for handling complex memory space.

.. toctree::
   :maxdepth: 1
   :caption: Using The Memory Interface:

   connecting
   master
   slave
   hub
   usingTcp
   blocks
   blocks_advanced
   classes/index

