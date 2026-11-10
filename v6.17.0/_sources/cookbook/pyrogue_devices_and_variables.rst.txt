.. _cookbook_pyrogue_devices_variables:

======================================
PyRogue Devices and Variables Recipes
======================================

Use these recipe-oriented pages for concrete examples:

- :doc:`/getting_started/pyrogue_tree_example/p_t_device`
- :doc:`/pyrogue_tree/core/remote_variable`
- :doc:`/pyrogue_tree/core/link_variable`
- :doc:`/pyrogue_tree/builtin_devices/data_receiver`

Recipe 1: Add A Memory-Backed Control Variable
==============================================

Problem
=======

Expose a hardware register field as a writable tree variable.

Procedure
=========

1. Define a ``RemoteVariable`` in your device.
2. Attach correct bit offset/size and access mode.
3. Validate read/write behavior from a simple client.

Deep Dive
=========

- :doc:`/pyrogue_tree/core/variable`
- :doc:`/pyrogue_tree/core/model`

Recipe 2: Create A Computed Status Value
========================================

Problem
=======

Expose a derived metric without adding new hardware registers.

Procedure
=========

1. Define a ``LinkVariable`` that depends on one or more source variables.
2. Keep computation deterministic and side-effect free.
3. Confirm update behavior during polling and command workflows.

Deep Dive
=========

- :doc:`/cookbook/advanced_pyrogue_patterns`
- :doc:`/pyrogue_tree/core/poll_queue`
