.. _pyrogue_core_tree_architecture:

============================
PyRogue Tree Architecture
============================

The PyRogue tree is the primary user-facing control model in Rogue.

Core structure:

- ``Root`` anchors the application and service lifecycle.
- ``Device`` nodes compose system hierarchy.
- ``Variable`` and ``Command`` nodes expose control and telemetry.
- ``Block`` and ``Model`` layers map values onto memory transactions.

Start with these pages:

- :doc:`/pyrogue_tree/index`
- :doc:`/pyrogue_tree/node/root/index`
- :doc:`/pyrogue_tree/node/device/index`
- :doc:`/pyrogue_tree/node/variable/index`
- :doc:`/pyrogue_tree/node/command/index`
- :doc:`/pyrogue_tree/model/index`

API reference:

- :doc:`/api/python/root`
- :doc:`/api/python/device`
- :doc:`/api/python/basevariable`
- :doc:`/api/python/basecommand`
