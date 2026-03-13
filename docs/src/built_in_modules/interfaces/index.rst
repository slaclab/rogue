.. _built_in_modules_interfaces:

==========
Interfaces
==========

Interfaces collects the adapters that connect a running PyRogue process to
external software, services, and host-side operational tooling. These pages
are primarily about ``pyrogue.interfaces.*`` helpers plus a small amount of
supporting Rogue runtime integration, rather than about the internal Stream or
Memory interfaces themselves.

These modules are the right choice when a design needs to persist state, bridge
into another host process, expose a control path outside Python, or enforce
runtime compatibility checks before the rest of the tree starts.

Subtopics
=========

- Use :doc:`sql` for SQL-backed logging of ``Variable`` values and syslog
  events.
- Use :doc:`version` for version-gating and startup compatibility checks.
- Use :doc:`cpp_api_wrapper` when a C++ application needs to create or control
  a PyRogue ``Root``.
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
