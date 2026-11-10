.. _tutorials:

=========
Tutorials
=========

Tutorials provide guided, end-to-end learning paths.

Scope of Tutorials:

- Build deeper understanding through complete workflows
- Explain tradeoffs and design patterns, not just first use
- Bridge into architecture-level sections after hands-on examples

New to Rogue? Start with :doc:`/getting_started/index` — it builds a complete
working application from scratch with no hardware required.

.. note::

   **Every tutorial below runs without hardware.** Rogue ships software
   endpoints — a memory emulator, an SRP emulator, a PRBS data generator — so
   each subsystem can be learned before a board is involved. Each tutorial's
   code lives in ``docs/src/tutorials/examples/`` and is executed by the test
   suite, so what you read is what runs.

The Learning Path
=================

Work through these in order, or jump to the subsystem you need. Each continues
from :doc:`/getting_started/index`.

.. list-table::
   :widths: 28 52 20
   :header-rows: 1

   * - Tutorial
     - What you learn
     - Builds on
   * - :doc:`protocol_stack`
     - Reach registers through SRP, then a TCP bridge, then a full
       UDP + RSSI + packetizer stack — swapping transports without touching
       the device.
     - Getting Started
   * - :doc:`commands_and_groups`
     - The three command flavours, how variables pack into Blocks (and why
       that decides transaction count), and how Groups filter bulk operations.
     - Getting Started
   * - :doc:`file_capture`
     - Write a stream to disk, replay it, and measure what compression
       actually buys.
     - Getting Started
   * - :doc:`custom_cpp_module`
     - Build a C++ stream module, load it into Python, and wrap it in a
       Device.
     - Stream interface
   * - :doc:`device_workflow_tutorial`
     - Turn a raw register map into a Device that documents itself.
     - Getting Started
   * - :doc:`system_integration_tutorial`
     - Assemble control, data, and remote access into one application.
     - Device workflow

Supplemental legacy step-by-step examples remain available in:

- :doc:`/advanced_examples/index`

.. toctree::
   :maxdepth: 1
   :caption: Tutorials:

   /getting_started/index
   protocol_stack
   commands_and_groups
   file_capture
   custom_cpp_module
   device_workflow_tutorial
   system_integration_tutorial
   /advanced_examples/index

Related Topics
==============

- Core tree architecture and lifecycle: :doc:`/pyrogue_tree/index`
- Installation and build workflows: :doc:`/installing/index`
