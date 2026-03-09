.. _pyrogue_tree_node_device_prbstx:

===================
PrbsTx Device Class
===================

:py:class:`~pyrogue.utilities.prbs.PrbsTx` is a PRBS transmitter device wrapper.

It exposes TX controls and counters through variables/commands such as
``txEnable``, ``txSize``, ``txPeriod``, ``genFrame``, and throughput/error
counters.

Logging
=======

The underlying Rogue PRBS engine uses Rogue C++ logging.

- Logger name: ``pyrogue.prbs.tx``
- Configuration API:
  ``rogue.Logging.setFilter('pyrogue.prbs.tx', rogue.Logging.Debug)``

Set the filter if you want detailed
transmit-path diagnostics.

PrbsTx API Reference
==========================

See :doc:`/api/python/utilities_prbs_prbstx` for generated API details.
