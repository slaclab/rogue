.. _pyrogue_tree_node_device_runcontrol:

=======================
RunControl Device Class
=======================

:py:class:`pyrogue.RunControl` is a :py:class:`pyrogue.Device` subclass for
software-driven run state management.

It provides:

* ``runState`` (for example ``Stopped`` / ``Running``)
* ``runRate`` (iteration frequency)
* ``runCount`` (loop counter)
* optional ``cmd`` callback executed each run loop iteration

Use it directly for simple DAQ orchestration, or subclass it to integrate
external run-control systems.

RunControl Class Documentation
==============================

.. autoclass:: pyrogue.RunControl
   :members:
   :member-order: bysource
   :inherited-members:
