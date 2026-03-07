.. _built_in_modules:

================
Built-in Modules
================

Built-in Modules collects core Rogue components that are commonly assembled
into complete systems: hardware interfaces, protocol stacks, utilities, and
integration helpers.

In practice, these modules are where transport and integration work gets done:

- Hardware links to FPGA/driver interfaces
- Protocol layers for framing, reliability, and remote register access
- Utility blocks for recording, playback, PRBS, and data conditioning
- Simulation and operations integrations used during development and testing

Most deployments combine this section with :doc:`/stream_interface/index`,
:doc:`/memory_interface/index`, and :doc:`/pyrogue_tree/index`.

Key integration topics
======================

- Simulation helpers for memory and link emulation:
  :doc:`/built_in_modules/simulation/index`
- SQL variable/system-log capture:
  :doc:`/built_in_modules/sql`
- Version checks and compatibility guards:
  :doc:`/built_in_modules/version`
- C++ wrapper entry point for embedding Rogue:
  :doc:`/built_in_modules/cpp_api_wrapper`
- OS-backed memory bridge components:
  :doc:`/built_in_modules/os_memory_bridge/index`

Built-in Module Subgroups
=========================

- Utility modules: :doc:`/built_in_modules/utilities/index`
- Hardware modules: :doc:`/built_in_modules/hardware/index`
- Protocol modules: :doc:`/built_in_modules/protocols/index`

.. toctree::
   :maxdepth: 1
   :caption: Built-in Modules:

   simulation/index
   sql
   version
   cpp_api_wrapper
   os_memory_bridge/index
   /built_in_modules/utilities/index
   /built_in_modules/hardware/index
   /built_in_modules/protocols/index
