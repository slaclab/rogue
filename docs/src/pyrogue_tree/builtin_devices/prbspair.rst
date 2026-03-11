.. _pyrogue_tree_node_device_prbspair:

=====================
PrbsPair Device Class
=====================

:py:class:`~pyrogue.utilities.prbs.PrbsPair` combines a PRBS TX and RX device
into a single convenience container.

It is useful for loopback tests and end-to-end PRBS validation where both
transmit and receive control should live under one node.

Logging
=======

``PrbsPair`` uses the same underlying Rogue C++ PRBS loggers as
:doc:`prbstx` and :doc:`prbsrx`:

- ``pyrogue.prbs.tx``
- ``pyrogue.prbs.rx``

Configure whichever side you are debugging:

.. code-block:: python

   import rogue

   rogue.Logging.setFilter('pyrogue.prbs.tx', rogue.Logging.Debug)
   rogue.Logging.setFilter('pyrogue.prbs.rx', rogue.Logging.Debug)

Related Topics
==============

- :doc:`/built_in_modules/utilities/prbs/index`
- :doc:`prbstx`
- :doc:`prbsrx`

API Reference
=============

- Python: :doc:`/api/python/utilities_prbs_prbspair`
