.. _pyrogue_tree_node_device_runcontrol:

=======================
RunControl Device Class
=======================

:py:class:`~pyrogue.RunControl` is a :py:class:`~pyrogue.Device` subclass for
software-driven run state management.

Use it directly for most software-driven data acquisition, or subclass it for
more complex hardware-integrated and external run-control workflows.

What RunControl Provides
========================

``RunControl`` packages a small software run loop into a normal tree-facing
``Device``. In the current implementation it provides:

* ``runState`` (for example ``Stopped`` / ``Running``)
* ``runRate`` (iteration frequency)
* ``runCount`` (loop counter)
* Optional ``cmd`` callback executed each run loop iteration

When ``runState`` is set to ``Running``, ``RunControl`` starts a background
thread. That thread sleeps for the selected ``runRate``, calls the optional
``cmd`` callback, and increments ``runCount``. When ``runState`` leaves the
running state, the thread exits and is joined.

This makes ``RunControl`` a good fit when the system needs a simple
operator-visible "start a repeating loop" control surface without building a
custom thread manager from scratch.

When To Use RunControl
======================

Use ``RunControl`` when the important behavior is a repeated loop whose state
should be visible and editable from the tree.

Common fits include:

* Software acquisition loops
* Periodic trigger or polling actions
* Application-level run/stop coordination
* Simple supervisory loops that call one function at a selected rate

If the operation is instead a one-shot or finite multi-step procedure, see
:doc:`process`.

What You Usually Set
====================

Most ``RunControl`` definitions use just a few parameters:

* ``hidden`` to keep the node in a dedicated run-control view rather than the
  normal tree display.
* ``rates`` to define the available loop-rate selections.
* ``states`` to define the available run-state labels.
* ``cmd`` for the function or command invoked once per loop iteration.

In practice, ``cmd`` and ``rates`` are the most important ones because they
define what the loop does and how fast it runs.

Subclassing And Override Points
===============================

In practice, subclassing is often the general way to use ``RunControl``.
Supplying ``cmd=...`` is enough for a simple periodic software loop, but many
real systems need start/stop behavior around hardware triggers, counters,
readout enables, or run bookkeeping.

In the current implementation, the main override points are:

* ``_setRunState`` to integrate with external run-control hardware or software
  when the state changes.
* ``_setRunRate`` when changing the selected rate should trigger additional
  application behavior.
* ``_run`` when the default "sleep, call ``cmd``, increment ``runCount``"
  loop is not sufficient.

Concrete Example
================

One common pattern is:

* When the run starts, read the current state, reset counters, and enable the
  hardware path that should produce data.
* While the run is active, wait for new frames or events and publish the
  accumulated count through ``runCount``.
* When the run stops, disable the same trigger or readout path cleanly.

This example reflects that style:

.. code-block:: python

   import pyrogue as pr
   import time

   class AcquisitionRunControl(pr.RunControl):
       def __init__(self, **kwargs):
           super().__init__(
               name='RunControl',
               description='Control a frame-based acquisition run',
               hidden=True,
               rates={0: 'Auto'},
               states={0: 'Stopped', 1: 'Running'},
               **kwargs,
           )

       def _start_run(self):
           # Capture the current state before enabling acquisition.
           self.root.ReadAll()

           trigger = self.root.TriggerRegisters
           trigger.ResetCounters()
           self.root.CountReset()

           trigger.Enable.set(True)

       def _stop_run(self):
           self.root.TriggerRegisters.Enable.set(False)

       def _run(self):
           self._start_run()
           self.runCount.set(0)

           try:
               while self.runState.valueDisp() == 'Running':
                   # Wait for one more recorded frame and publish the total.
                   channel = self.root.DataWriter.getChannel(1)
                   channel.waitFrameCount(self.runCount.value() + 1, 1000000000)
                   self.runCount.set(channel.getFrameCount())
                   time.sleep(0.01)
           finally:
               self._stop_run()

Related Topics
==============

* Structured long-running procedures: :doc:`process`
* Root lifecycle and top-level orchestration: :doc:`/pyrogue_tree/core/root`
* Device composition and startup behavior: :doc:`/pyrogue_tree/core/device`

API Reference
=============

See :doc:`/api/python/pyrogue/runcontrol` for generated API details.
