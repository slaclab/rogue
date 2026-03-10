.. _pyrogue_tree_node_device_prbsrx:

===================
PrbsRx Device Class
===================

:py:class:`~pyrogue.utilities.prbs.PrbsRx` is a PRBS receiver device wrapper.

It exposes receiver controls and counters as PyRogue variables/commands, for
example ``rxEnable``, ``rxErrors``, ``rxCount``, ``rxRate``, and payload-check
controls.

Logging
=======

The underlying Rogue PRBS engine uses Rogue C++ logging.

- Logger name: ``pyrogue.prbs.rx``
- Unified Logging API:
  ``logging.getLogger('pyrogue.prbs.rx').setLevel(logging.DEBUG)``
- Legacy Logging API:
  ``rogue.Logging.setFilter('pyrogue.prbs.rx', rogue.Logging.Debug)``

Set the filter if you want detailed
receive-path diagnostics.

PrbsRx API Reference
==========================

See :doc:`/api/python/utilities_prbs_prbsrx` for generated API details.
