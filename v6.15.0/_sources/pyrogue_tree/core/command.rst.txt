.. _pyrogue_tree_node_command:

=======
Command
=======

Commands are the action-oriented Nodes in the PyRogue tree. Where Variables
represent state, Commands represent intent: reset something, apply something,
start something, stop something, or trigger a hardware-defined action.

That distinction is important because PyRogue trees are not just for exposing
register values. They are also used to expose procedures and operator actions
in a structured, scriptable way.

What Commands Are For
=====================

Commands are used whenever the important interaction is "do this" rather than
"set this value and leave it there."

Typical examples include:

* Reset and initialization actions.
* File or configuration workflows.
* Multi-step software procedures.
* Hardware trigger or strobe registers.

A Command is still closely related to the Variable model in PyRogue, but the
main point of a Command is invocation behavior rather than persistent state.

How Commands Are Invoked
========================

Commands can be invoked either directly or through ``call``:

* ``cmd(arg)``
* ``cmd.call(arg)``

That makes them easy to use in both interactive Python workflows and in higher
level tooling that wants to treat tree actions as first-class Nodes.

Choosing Between Local And Remote Commands
==========================================

PyRogue provides two main Command forms:

.. toctree::
   :maxdepth: 1
   :hidden:

   local_command
   remote_command

Use them based on where the action really lives:

* :doc:`/pyrogue_tree/core/local_command` for software-defined actions
  implemented in Python.
* :doc:`/pyrogue_tree/core/remote_command` for actions backed by hardware
  register writes or similar remote transaction paths.

That distinction is similar to the distinction between local and remote
Variables: one lives in software behavior, the other is tied to the hardware
access path.

Commands In Tree Design
=======================

Good Command design usually follows the same rule as good Variable design:
expose the action at the level where a user naturally expects to find it.

In practice:

* Put system-wide actions on ``Root`` when they affect the whole tree.
* Put subsystem-specific actions on the relevant ``Device``.
* Prefer descriptive, operator-readable command names over implementation
  details.

That keeps remote tools, GUIs, and scripts easier to understand, because the
tree reads like an interface rather than like an internal implementation dump.

Commands Vs Variables
=====================

Some hardware actions can be modeled either as a writable Variable or as a
Command. When choosing between them, ask whether the user is expressing state
or requesting an action.

Examples:

* A persistent enable bit is usually better modeled as a Variable.
* A reset pulse or self-clearing trigger is usually better modeled as a
  Command.

This distinction matters because it makes the tree more intuitive for users and
for GUIs such as PyDM. A well-chosen Command reads like an operation, not like
an awkward pseudo-register.

What To Explore Next
====================

* Python-defined actions: :doc:`/pyrogue_tree/core/local_command`
* Hardware-backed actions: :doc:`/pyrogue_tree/core/remote_command`
* Device placement and operational hooks: :doc:`/pyrogue_tree/core/device`
* Root-level system actions: :doc:`/pyrogue_tree/core/root`

API Reference
=============

See :doc:`/api/python/pyrogue/basecommand` for generated API details.
