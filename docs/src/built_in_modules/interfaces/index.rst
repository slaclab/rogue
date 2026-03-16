.. _built_in_modules_interfaces:

==========
Interfaces
==========

Interface modules are the adapters that connect a running PyRogue tree to
other processes, external services, and deployment tooling. They are often the
boundary where control software, data persistence, and host integration meet.

In practice, these modules are used when a system needs to expose tree state
outside the process boundary, persist operational data, or embed PyRogue
control into a larger C++ runtime.

Use this subsection to choose the integration path:

- Use :doc:`sql` for SQL-backed logging of Variable values and syslog events.
- Use :doc:`version` for version-gating and compatibility checks at startup.
- Use :doc:`cpp_api_wrapper` when embedding and controlling a PyRogue Root
  from C++.
- Use :doc:`os_memory_bridge` when exposing OS-level commands through a memory
  transaction interface.

These modules are typically combined with the Core tree model in
:doc:`/pyrogue_tree/core/index`, and with transport layers from
:doc:`/stream_interface/index` or :doc:`/memory_interface/index`.

.. toctree::
   :maxdepth: 1
   :caption: Interfaces:

   sql
   version
   cpp_api_wrapper
   os_memory_bridge
