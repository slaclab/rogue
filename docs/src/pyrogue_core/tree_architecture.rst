.. _pyrogue_core_tree_architecture:

============================
PyRogue Tree Architecture
============================

The PyRogue tree is the primary user-facing control model in Rogue. It gives
you a hierarchical namespace for control, status, and data-path coordination.

Core structure
==============

- ``Root`` anchors the application and service lifecycle.
- ``Device`` nodes compose system hierarchy.
- ``Variable`` and ``Command`` nodes expose control and telemetry.
- ``Block`` and ``Model`` layers map values onto memory transactions.

How the layers fit together
===========================

1. Application bootstraps a ``Root`` object.
2. ``Device`` instances are added to construct the control tree.
3. Variables and commands define the user-facing interface.
4. Blocks and models translate between tree values and memory operations.
5. Client interfaces expose the tree over network and UI tooling.

Design guidance
===============

- Use ``Device`` boundaries to reflect hardware or subsystem ownership.
- Keep variable naming and units consistent across sibling devices.
- Prefer small, composable devices over one very large monolithic device.
- Reserve model-specific conversion logic for model classes.

Related usage topics
====================

- Client access and remote tree interaction: :doc:`/pyrogue_core/client_access`
- Polling design for changing values: :doc:`/pyrogue_core/polling`
- Configuration/state persistence: :doc:`/pyrogue_core/yaml_state_config`

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
