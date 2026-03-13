.. _built_in_modules:

================
Built-in Modules
================

Built-in Modules is the entry point for Rogue functionality that lives below
the top-level ``pyrogue`` namespace. These pages are organized for discovery
first, but they also make the namespace split explicit so it is clear whether
you are working with a top-level PyRogue ``Device``, a submodule wrapper, or a
lower-level Rogue endpoint.

Three layers matter when choosing a module family:

- ``pyrogue``
  Top-level tree-facing classes such as ``RunControl``, ``Process``,
  ``DataWriter``, and ``DataReceiver``. Those are documented in
  :doc:`/pyrogue_tree/builtin_devices/index`.
- ``pyrogue.<submodule>``
  Python integrations and wrapper devices such as
  ``pyrogue.utilities.fileio.StreamWriter`` or
  ``pyrogue.protocols.UdpRssiPack``.
- ``rogue.<submodule>``
  Lower-level exported Rogue modules such as
  ``rogue.utilities.fileio.StreamWriter`` or
  ``rogue.protocols.udp.Client``.

Most systems use more than one of these layers at once. A tree often exposes
top-level ``pyrogue`` devices for operations and monitoring, then relies on
``pyrogue.<submodule>`` wrappers or direct ``rogue.<submodule>`` endpoints to
handle file I/O, protocol transport, simulation, or hardware access.

Choosing A Subsection
=====================

- :doc:`/built_in_modules/utilities/index`
  Stream-support modules such as file I/O, PRBS, compression, and HLS helpers.
- :doc:`/built_in_modules/protocols/index`
  Transport, framing, and register-access layers such as UDP, RSSI, SRP,
  packetizer, batcher, Xilinx, UART, and GPIB-related helpers.
- :doc:`/built_in_modules/interfaces/index`
  External integration helpers such as SQL logging, C++ embedding, version
  checks, and OS-backed memory bridges.
- :doc:`/built_in_modules/hardware/index`
  Driver-backed hardware endpoints that connect host software to firmware data
  paths.
- :doc:`/built_in_modules/simulation/index`
  Software-only stand-ins for memory and link behavior used during development
  and integration testing.

Related Topics
==============

- Top-level PyRogue built-ins: :doc:`/pyrogue_tree/builtin_devices/index`
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
