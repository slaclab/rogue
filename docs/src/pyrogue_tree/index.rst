.. _pyrogue_tree:

================
PyRogue Tree
================

The PyRogue Tree implements a tree structure for the hierarchical organization of devices.
All devices, variables, and commands subclass from :ref:`pyrogue_tree_node`.

The tree structure is arbitrary and does not necessarily follow the hardware bus structures.
Elements within the tree are exposed to outside systems via the various :ref:`management interfaces<interfaces>` (epics, pyro, mysql, etc)

A common hierarchy will be a Root Node connected to any number of Device Nodes, which each can have their own Device Nodes, Command Nodes, and Variable Nodes.

.. toctree::
   :maxdepth: 2
   :caption: Node Class Structure:

   node/index
   root/index
   device/index
   command/index
   variable/index

.. toctree::
   :maxdepth: 1
   :caption: Classes Utilizing Node:

   root/index
   device/index
   command/index
   variable/index