.. _pyrogue_tree_node_device_process:

====================
Process Device Class
====================

:py:class:`~pyrogue.Process` packages a long-running or multi-step operation
into a tree-facing ``Device`` with built-in commands and status Variables. In
the current implementation it provides:

* Start/stop commands
* Running/progress/message status variables
* Optional argument and return variables
* Optional wrapped function callback

Use it when an operation needs structured status reporting and GUI visibility.

The process runs in a background thread. While it is active, the tree can
report whether it is running, how far along it is, and any status message the
implementation wants to expose.

When To Use Process
===================

Use ``Process`` when the important interaction is "start this procedure and
track it while it runs."

Common fits include:

* Calibration or tuning sequences
* Capture/export workflows
* Long-running initialization or verification steps
* Procedures that need operator-visible progress and status text

If the action is instead a continuous repeating loop with a run/stop state and
a selected loop rate, see :doc:`run_control`.

What You Usually Set
====================

Most ``Process`` definitions revolve around three constructor-level extension
points:

* ``function`` for the process body
* ``argVariable`` for tree-visible input arguments
* ``returnVariable`` for tree-visible return data

For simple use, supplying ``function=...`` is enough. The wrapper passes
keyword arguments named ``root``, ``dev``, and ``arg``, and the function may
accept any subset of those names.

In practice, many real systems also add process-specific ``LocalVariable``
Nodes for inputs, tuning knobs, captured results, or plotting helpers. That is
often what makes a ``Process`` feel like a usable operator-facing workflow
rather than just a background thread.

Subclassing And Override Points
===============================

In practice, subclassing is often the general way to use ``Process``.
Supplying ``function=...`` is enough for a compact wrapper, but many real
systems need additional Variables, explicit progress reporting, and process
logic that touches a wider subtree.

The usual extension points are:

* Add process-specific Variables in ``__init__`` for inputs, outputs, or
  operator controls.
* Pass ``function=self._my_wrapper`` when a wrapper-style callback is enough.
* Override ``_process()`` directly when the full body of the procedure belongs
  on the subclass.

The built-in status Variables are:

* ``Running`` for whether the thread is active
* ``Progress`` for fractional completion
* ``Message`` for operator-facing status text
* ``Step`` and ``TotalSteps`` for step-count style progress reporting

If you provide ``argVariable`` and ``returnVariable``, they can be used to
pass one tree-visible argument into the procedure and publish one result back
out through the tree.

There are two common ways to drive ``Progress``:

* Call ``setProgress(value)`` when the procedure naturally reports fractional
  completion on its own.
* Use ``setTotalSteps()``, ``setStep()``, and ``incrementSteps()`` when the
  procedure is naturally step-based and ``Progress`` should be derived from
  ``Step`` and ``TotalSteps``.

The second pattern is often clearer for iterative procedures, while the first
fits algorithms whose completion metric is not naturally "step N out of M."

Direct writes to ``Progress``, ``Step``, and ``TotalSteps`` are also supported
for compatibility with existing code. ``Progress`` is clamped into the valid
``0.0`` to ``1.0`` range, and step-based progress recomputes automatically
when ``Step`` or ``TotalSteps`` changes. The older ``_setSteps()`` and
``_incrementSteps()`` helpers remain available as compatibility wrappers, but
new code should prefer the public methods above.

Concrete Example
================

One common pattern is a calibration or tuning process that adds its own
operator-facing settings and result storage, then updates ``Message``,
``Progress``, ``Step``, and ``TotalSteps`` while it runs.

.. code-block:: python

   import pyrogue as pr
   import time

   class CaptureProcess(pr.Process):
       def __init__(self, **kwargs):
           super().__init__(description='Capture N samples', **kwargs)

           # Tree-facing input that lets the operator choose how much work to do.
           self.add(pr.LocalVariable(
               name='SampleCount',
               mode='RW',
               value=100,
               description='Number of samples to capture',
           ))

           # Hidden result storage for whatever data the process produces.
           self.add(pr.LocalVariable(
               name='CaptureResult',
               mode='RO',
               value=[],
               hidden=True,
               description='Captured result data',
           ))

       def _process(self):
           # Batch update notifications while the process runs. PyRogue still
           # publishes changes during the block, but it coalesces them so GUIs
           # and remote listeners do not get spammed on every individual write.
           with self.root.updateGroup(period=0.25):
               total = self.SampleCount.value()
               captured = []

               # Initialize the built-in status Variables before starting work.
               self.Message.setDisp('Running capture')
               self.setTotalSteps(total)
               self.setStep(0)
               self.setProgress(0.0)

               for i in range(total):
                   # Respect the built-in Stop command.
                   if self._runEn is False:
                       self.Message.setDisp('Stopped by user')
                       return

                   # Do one unit of hardware or software work.
                   time.sleep(0.01)
                   captured.append(i)

                   # setStep() updates Step and recomputes Progress together.
                   self.setStep(i + 1)

               # Publish the final result back into the tree.
               self.CaptureResult.set(captured)
               self.Message.setDisp('Done')

Invocation Patterns
===================

``Process`` can be started either through the built-in ``Start`` command or by
calling the object directly with an optional argument:

* ``my_process.Start()``
* ``my_process()``
* ``my_process(arg)``

When an argument is supplied and ``argVariable`` exists, the argument is first
written to that Variable before the background thread starts.

Design Guidance
===============

Good ``Process`` implementations usually:

* Update ``Message`` with short operator-facing status text
* Prefer ``setProgress()`` for fractional progress and ``setTotalSteps()``,
  ``setStep()``, or ``incrementSteps()`` for step-based progress
* Add explicit input or result Variables when the procedure needs operator
  parameters or produces structured output
* Check the stop condition when the work can be interrupted cleanly
* Use ``root.updateGroup(...)`` when the body will publish many updates over
  time

Related Topics
==============

* Repeating run loops and run-state control: :doc:`run_control`
* Command behavior: :doc:`/pyrogue_tree/core/command`
* Device composition and lifecycle: :doc:`/pyrogue_tree/core/device`
* Lower-level transport, protocol, and utility families: :doc:`/built_in_modules/index`

API Reference
=============

See :doc:`/api/python/pyrogue/process` for generated API details.
