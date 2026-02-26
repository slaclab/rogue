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

Example
=======

.. code-block:: python

   import pyrogue as pr
   import time

   class CaptureProcess(pr.Process):
       def __init__(self, **kwargs):
           super().__init__(description='Capture N samples', function=self._process, **kwargs)

       def _process(self):
           with self.root.updateGroup(period=0.25): # Allow 0.25s between publishing variable updates while running
               self.Message.setDisp('Running capture')
               self.TotalSteps.set(100)
               self.Step.set(0)

               for i in range(100):
                   if self._runEn is False:
                       self.Message.setDisp('Stopped by user')
                       return
                   # Do one unit of work
                   time.sleep(0.01)
                   self._setSteps(i + 1)

               self.Message.setDisp('Done')

Process Class Documentation
===========================

See :doc:`/api/python/process` for generated API details.
