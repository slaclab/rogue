.. _pyrogue_core_advanced_patterns:

=================
Advanced Patterns
=================

Advanced PyRogue usage commonly includes:

- Device method overrides and composition patterns
- Complex ``RemoteVariable`` bit mappings
- Computed ``LinkVariable`` dependencies

Design principles
=================

- Keep base ``Device`` classes predictable; isolate special behavior in narrow
  overrides.
- Favor declarative variable definitions over implicit runtime mutation.
- Keep link-variable dependency graphs shallow and well documented.

Common failure modes
====================

- Hidden side effects inside command callbacks.
- Overloaded variables that mix control intent and status reporting.
- Circular or fragile link-variable dependencies.

Validation checklist
====================

- Commands are deterministic for the same input state.
- Variable update flows are understandable from docs and code together.
- Unit and range semantics are explicitly documented.

Starting points:

- :doc:`/pyrogue_tree/core/device/index`
- :doc:`/pyrogue_tree/core/variable/remote_variable/index`
- :doc:`/pyrogue_tree/core/variable/link_variable/index`

API reference:

- :doc:`/api/python/device`
- :doc:`/api/python/remotevariable`
- :doc:`/api/python/linkvariable`
