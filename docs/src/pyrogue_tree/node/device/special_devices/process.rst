.. _pyrogue_tree_node_device_process:

====================
Process Device Class
====================

:py:class:`pyrogue.Process` is a helper device for long-running or multi-step
operations that should be managed as part of the tree.

It provides:

* start/stop commands
* running/progress/message status variables
* optional argument and return variables
* optional wrapped function callback

Use it when an operation needs structured status reporting and GUI visibility.

Process Class Documentation
===========================

.. autoclass:: pyrogue.Process
   :members:
   :member-order: bysource
   :inherited-members:
