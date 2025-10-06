.. _pyrogue_tree_node_device_runcontrol:

RunControl Device Class
=======================

* :py:class:`pyrogue.RunControl` is a sub-class of :py:class:`pyrogue.Device` which serves as the base class for application specific run control.

   * Can be used as is for most software driven data acquisition
   * Can be sub-classed for more complex hardware and external run control

* The RunControl object is created the following way:

.. code-block:: python

   Rc = pyrogue.RunControl(name, description, 
                           hidden=True, rates, states, cmd)

* Parameters:

   * Hidden is normally True since RunControl does not appear in the normal GUI tree, instead it is represented in a special window.
   * rates: A dictionary of rates and associated keys. The keys are application specific and represent the run rate in hz in the default class. The defaults rates are:

      * rates={1:'1 Hz', 10:'10 Hz'}

   * states: A dictionary of states and associated keys. The keys are application specific. The default rates are:

      * states={0:'Stopped', 1:'Running'}

   * cmd: Is the command to execute at each iteration when using the default software driven run() method. This can either be a pointer to a python function or pyrogue Command.

RunControl Class Documentation
==============================

.. autoclass:: pyrogue.RunControl
   :members:
   :member-order: bysource
   :inherited-members: