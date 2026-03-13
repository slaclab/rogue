.. _built_in_modules:

================
Built-in Modules
================

Built-in Modules collects core Rogue components that are commonly assembled
into complete systems: hardware interfaces, protocol stacks, utilities, and
integration helpers.

This section intentionally mixes three kinds of building blocks:

- exported Rogue C++ modules that are exposed into Python
- pure Python helper modules
- Python ``Device`` wrappers around lower-level Rogue modules

That third category is important when a lower-level stream or utility object
also has a tree-managed wrapper. In those cases, the built-in-modules pages
cover both the core module behavior and the wrapper layer, while
:doc:`/pyrogue_tree/builtin_devices/index` stays focused on classes exposed in
the top-level ``pyrogue`` namespace.

In practice, this section is where transport and system-integration work gets
done:

- Hardware links to FPGA/driver interfaces
- Protocol layers for framing, reliability, and remote register access
- Utility blocks for recording, playback, PRBS, and data conditioning
- Simulation and operations integrations used during development and testing

Most deployments combine this section with :doc:`/stream_interface/index`,
:doc:`/memory_interface/index`, and :doc:`/pyrogue_tree/index`.

Subsection guide
================

- :doc:`/built_in_modules/interfaces/index`
  Interface adapters and integration helpers such as SQL logging, version
  checks, C++ API wrapping, and OS-backed memory bridges.
- :doc:`/built_in_modules/simulation/index`
  Software-only stand-ins for memory/link behavior used in bring-up and
  integration testing.
- :doc:`/built_in_modules/protocols/index`
  Transport/control protocol layers (UDP, RSSI, SRP, packetizer, batcher,
  Xilinx, EPICS, UART).
- :doc:`/built_in_modules/hardware/index`
  Hardware-facing modules and driver-backed interfaces (AXI and raw access).
- :doc:`/built_in_modules/utilities/index`
  Reusable utility components for file I/O, PRBS, compression, and related
  support workflows.

Related Topics
==============

- Stream dataflow architecture: :doc:`/stream_interface/index`
- Memory transaction architecture: :doc:`/memory_interface/index`
- PyRogue tree composition and lifecycle: :doc:`/pyrogue_tree/index`

.. toctree::
   :maxdepth: 1
   :caption: Built-in Modules:

   interfaces/index
   simulation/index
   protocols/index
   hardware/index
   utilities/index
