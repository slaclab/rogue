.. _pyrogue_tree:

============
PyRogue Tree
============

PyRogue organizes application control around a hierarchical tree owned by one
running ``Root``. That tree is where hardware abstractions, operator-facing
controls, background activity, and remote access meet.

Most PyRogue work starts with the tree, even when the real task is hardware
control, register definition, data movement, or GUI integration. The tree is
the layer that gives those lower-level pieces a stable user-facing structure:
``Device`` Nodes describe the system, ``Variable`` and ``Command`` Nodes expose
state and actions, and client interfaces make that structure visible to tools.

The section is organized in the same order most users need to learn it:

* :doc:`core/index` explains the object model and runtime behavior of
  ``Root``, ``Device``, ``Variable``, ``Command``, ``Block``, and ``Model``.
  Start here if you are building or extending a tree.
* :doc:`builtin_devices/index` covers reusable ``Device`` implementations for
  common workflows such as run control, PRBS, stream read/write, and process
  control.
* :doc:`client_interfaces/index` covers the server/client access patterns used
  by scripts, GUIs, notebooks, and command-line tools.

Architectural View
==================

The tree model is intentionally independent from hardware bus topology.
You can optimize memory and stream transport plumbing for performance while
keeping a stable user-facing organization in the tree.

That separation is important because it lets one design serve multiple needs at
once. The same running ``Root`` can:

- Present a coherent register and control hierarchy to operators.
- Reuse built-in ``Device`` helpers for common behaviors.
- Expose the same live tree to PyDM, command-line clients, notebooks, or other
  remote consumers.

Reading Path
============

If you are new to this part of the docs, the most useful order is:

1. Read :doc:`/pyrogue_tree/core/index` to understand the tree model and the
   role of ``Root``.
2. Continue into the core pages for ``Root``, ``Device``, ``Variable``, and
   ``Command``.
3. Move to built-in Devices once the composition model is clear.
4. Read client interfaces after you know how the tree is organized internally.

.. toctree::
   :maxdepth: 1
   :caption: PyRogue Tree:

   Components And Concepts <core/index>
   builtin_devices/index
   client_interfaces/index
