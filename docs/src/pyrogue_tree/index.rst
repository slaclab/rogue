.. _pyrogue_tree:

============
PyRogue Tree
============

PyRogue organizes application control around a hierarchical tree owned by one
running ``Root``. That tree is where hardware abstractions, operator-facing
controls, background activity, and remote access meet.

The section is split into three complementary topics:

* :doc:`core/index`: the Node model and lifecycle behavior for Root, Device,
  Variable, Command, Block, and Model.
* :doc:`builtin_devices/index`: reusable Device implementations for common
  workflows such as run control, PRBS, stream read/write, and process control.
* :doc:`client_interfaces/index`: server/client access patterns for scripts,
  GUIs, notebooks, and command-line tools.

Architectural view
==================

The tree model is intentionally independent from hardware bus topology.
You can optimize memory and stream transport plumbing for performance while
keeping a stable user-facing organization in the tree.

In practice:

- The Core layer defines the basic structures for composing the tree.
- Built-in Devices provide production-ready composition pieces inside that tree.
- Client interfaces expose one running Root to multiple concurrent tools.

Where to explore next
=====================

- Core Node model and lifecycle: :doc:`/pyrogue_tree/core/index`
- Built-in Device catalog: :doc:`/pyrogue_tree/builtin_devices/index`
- Client/server access patterns: :doc:`/pyrogue_tree/client_interfaces/index`

.. toctree::
   :maxdepth: 1
   :caption: PyRogue Tree:

   core/index
   builtin_devices/index
   client_interfaces/index
