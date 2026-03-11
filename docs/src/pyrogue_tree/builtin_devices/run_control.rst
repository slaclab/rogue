.. _pyrogue_tree_node_device_runcontrol:

=======================
RunControl Device Class
=======================

:py:class:`~pyrogue.RunControl` is a :py:class:`~pyrogue.Device` subclass for
software-driven run state management.

Use it directly for most software-driven data acquisition, or subclass it for
more complex hardware-integrated and external run-control workflows.

It provides built-in fields such as:

* ``runState`` (for example ``Stopped`` / ``Running``)
* ``runRate`` (iteration frequency)
* ``runCount`` (loop counter)
* Optional ``cmd`` callback executed each run loop iteration

Construction
------------
``RunControl`` is typically created as:

.. code-block:: python

   rc = pyrogue.RunControl(
       name='RunControl',
       description='Application run controller',
       hidden=True,
       rates={1: '1 Hz', 10: '10 Hz'},
       states={0: 'Stopped', 1: 'Running'},
       cmd=myRunCommand,
   )

Parameters
----------
Key constructor parameters:

* ``hidden``: Normally ``True`` so RunControl appears in a dedicated run-control
  view instead of the normal tree display.
* ``rates``: Dictionary mapping application-specific rate keys to labels.
  In the default implementation, keys represent loop rates in Hz.
* ``states``: Dictionary mapping application-specific state keys to labels.
* ``cmd``: Callable executed at each iteration in the default software-driven
  run loop. This can be a Python function reference or a PyRogue command.

Related Topics
==============

- :doc:`process`
- :doc:`/pyrogue_tree/core/root`

API Reference
=============

- Python: :doc:`/api/python/pyrogue/runcontrol`
