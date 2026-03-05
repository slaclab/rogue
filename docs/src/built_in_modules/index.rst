.. _built_in_modules:

================
Built-in Modules
================

Built-in Modules collects core Rogue components that are commonly assembled
into complete systems: hardware interfaces, protocol stacks, utilities, and
integration helpers.

In practice, these modules are where transport and integration work gets done:

- hardware links to FPGA/driver interfaces
- protocol layers for framing, reliability, and remote register access
- utility blocks for recording, playback, PRBS, and data conditioning
- simulation and operations integrations used during development and testing

Most deployments combine this section with :doc:`/stream_interface/index`,
:doc:`/memory_interface/index`, and :doc:`/pyrogue_core/index`.

Key integration topics
======================

- Simulation helpers for memory and link emulation:
  :doc:`/built_in_modules/simulation/index`
- SQL variable/system-log capture:
  :doc:`/built_in_modules/sql`
- Version checks and compatibility guards:
  :doc:`/built_in_modules/version`

Where to explore next
=====================

- Utility modules: :doc:`/utilities/index`
- Hardware modules: :doc:`/hardware/index`
- Protocol modules: :doc:`/protocols/index`

.. toctree::
   :maxdepth: 1
   :caption: Built-in Modules:

   simulation/index
   sql
   version
   /utilities/index
   /hardware/index
   /protocols/index
