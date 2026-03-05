.. _pyrogue_core_variables_and_streams:

==============================
Variables and Variable Streams
==============================

PyRogue variables can be bound to memory-backed values, computed links, or
local software-only state. Variable stream interfaces are available for
integrating variable updates into stream-style flows.

Variable categories
===================

- ``RemoteVariable``: memory-backed fields mapped through blocks/models.
- ``LocalVariable``: software-owned state with no direct bus transaction.
- ``LinkVariable``: computed values derived from other variables or callbacks.

When to use each
================

- Use ``RemoteVariable`` for register and memory map representation.
- Use ``LocalVariable`` for runtime metadata, counters, and app-local settings.
- Use ``LinkVariable`` when values are computed, aggregated, or transformed.

Variable stream patterns
========================

Variable streams are useful when variable updates need to connect into stream
processing paths or external interfaces.

- Use stream-variable adapters for event-oriented update flows.
- Keep conversion logic explicit so stream payload meaning remains clear.
- Prefer narrative workflow docs first, then API details as needed.

Start with:

- :doc:`/pyrogue_tree/node/variable/index`
- :doc:`/pyrogue_core/python_interfaces/memory_stream_variable`

API reference:

- :doc:`/api/python/remotevariable`
- :doc:`/api/python/linkvariable`
- :doc:`/api/python/localvariable`
- :doc:`/api/python/interfaces_stream_variable`
