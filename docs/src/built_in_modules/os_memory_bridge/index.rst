.. _built_in_modules_os_memory_bridge:

================
OS Memory Bridge
================

The OS memory bridge pattern maps memory transactions to host-side Python
functions so standard ``RemoteVariable`` access can target non-hardware data
sources.

The two components are typically used together:

- :doc:`os_command_memory_slave`: Memory ``Slave`` adapter that decodes
  transactions and dispatches address-mapped command callbacks.
- :doc:`osmemmaster`: Example ``Device`` that defines matching
  ``RemoteVariable`` offsets/types against that slave.

This pairing is useful for prototyping register maps, exposing host metrics in
a tree, and testing memory-control paths before firmware is available.

.. toctree::
   :maxdepth: 1
   :caption: OS Memory Bridge:

   os_command_memory_slave
   osmemmaster
