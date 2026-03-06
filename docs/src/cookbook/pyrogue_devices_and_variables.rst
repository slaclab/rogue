.. _cookbook_pyrogue_devices_variables:

======================================
PyRogue Devices and Variables Recipes
======================================

Use these recipe-oriented pages for concrete examples:

- :doc:`/getting_started/pyrogue_tree_example/p_t_device`
- :doc:`/pyrogue_tree/node/variable/remote_variable/index`
- :doc:`/pyrogue_tree/node/variable/link_variable/index`
- :doc:`/pyrogue_tree/node/device/special_devices/data_receiver`

Recipe 1: Add a memory-backed control variable
==============================================

Problem
=======

Expose a hardware register field as a writable tree variable.

Procedure
=========

1. Define a ``RemoteVariable`` in your device.
2. Attach correct bit offset/size and access mode.
3. Validate read/write behavior from a simple client.

Deep dive
=========

- :doc:`/pyrogue_tree/node/variable/index`
- :doc:`/pyrogue_tree/model`

Recipe 2: Create a computed status value
========================================

Problem
=======

Expose a derived metric without adding new hardware registers.

Procedure
=========

1. Define a ``LinkVariable`` that depends on one or more source variables.
2. Keep computation deterministic and side-effect free.
3. Confirm update behavior during polling and command workflows.

Deep dive
=========

- :doc:`/pyrogue_core/advanced_patterns`
- :doc:`/pyrogue_tree/node/root/poll_queue`
