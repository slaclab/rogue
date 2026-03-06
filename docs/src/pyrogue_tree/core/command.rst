.. _pyrogue_tree_node_command:

=======
Command
=======

Commands are executable Nodes used to trigger actions in the tree.

A Command is still a Variable-like Node (inherits from
:py:class:`pyrogue.BaseVariable`), but its main purpose is invoking callable
behavior.

Command types
=============

* :py:class:`pyrogue.BaseCommand`: base class
* :py:class:`pyrogue.LocalCommand`: software-only Command
* :py:class:`pyrogue.RemoteCommand`: Command tied to a hardware register write

Commands can be invoked either directly or with ``call``:

* ``cmd(arg)``
* ``cmd.call(arg)``

Subtypes
========

.. toctree::
   :maxdepth: 1
   :caption: Command Subtypes:

   local_command
   remote_command

BaseCommand API Reference
===============================

See :doc:`/api/python/basecommand` for generated API details.
