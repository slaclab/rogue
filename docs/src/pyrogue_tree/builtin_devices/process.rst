.. _pyrogue_tree_node_device_process:

====================
Process Device Class
====================

:py:class:`~pyrogue.Process` packages a long-running or multi-step operation
into a tree-facing ``Device`` with built-in commands and status Variables. In
the current implementation it provides:

* Start/stop commands
* Cooperative pause/resume commands for procedures with safe checkpoints
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
* ``Paused`` for whether the worker is waiting at a pause checkpoint
* ``Progress`` for fractional completion
* ``Message`` for operator-facing status text
* ``Step`` and ``TotalSteps`` for step-count style progress reporting
* ``UpdatePeriod`` (hidden, default ``1.0`` s) for the ``updateGroup`` leak period

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
           # The base _run() already wraps _process() in an updateGroup context.
           # Tune the leak period via the inherited UpdatePeriod Variable instead
           # of opening a nested context here.
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

The ``Stop`` command requests a cooperative stop and waits for the worker to
exit. A callback should check ``dev._runEn`` and return when it becomes false.
When a supplied ``function`` returns normally, the base class reports ``Done``
and sets ``Progress`` to ``1.0``. If a stop was requested, it preserves the
current progress and reports ``Stopped``, retaining any callback message that
already begins with ``Stopped`` or ``Error:``. The callback's return value is
published in either case. Subclasses that override ``_process()`` manage their
own terminal status and progress.

Cooperative Pause And Resume
============================

Call ``pausePoint()`` from the worker between atomic operations to support
pausing. ``Pause`` requests a pause and returns immediately; ``Paused`` becomes
true only when the worker reaches a checkpoint. A function that never calls
``pausePoint()`` continues running normally. Pausing preserves the worker
thread, local variables, progress, and status message; ``Running`` stays true.

``Resume`` releases a paused worker or cancels a request that has not yet
reached a checkpoint. ``Start`` and direct invocation still start new runs;
they do not resume or replace an active worker. ``Pause`` and ``Resume`` do
nothing when idle. ``Stop`` wakes a paused worker, makes ``pausePoint()`` return
false, and waits for the worker to exit. Always return from the process body
when a checkpoint returns false. Pause state is cleared on completion, stop,
or error, including requests that never reached a checkpoint.

For example, supply this callback as ``function=capture``:

.. code-block:: python

   def capture(dev):
       samples = []
       dev.setTotalSteps(100)
       for i in range(100):
           if not dev.pausePoint():
               return samples
           # Replace this with one complete, indivisible acquisition operation.
           samples.append(i)
           dev.incrementSteps()
       return samples

A checkpoint may accept ``publish=callback`` to publish a partial result before
acknowledging a pause. This no-argument callback executes on the process worker
only when a pause is pending, without holding the process lock. Its exceptions
follow the usual process error path. For example, if a process has a
``PartialResult`` Variable, call
``dev.pausePoint(publish=lambda: dev.PartialResult.set(list(samples)))``.
If Resume or Stop arrives during publication, the worker rechecks the request
and does not wait. Stop still waits for publication and the worker to finish.

Before blocking, the checkpoint queues pending updates for listeners, including
the published result and ``Paused``, even inside nested ``updateGroup`` scopes
or with ``UpdatePeriod = 0``. It also queues the cleared ``Paused`` status on
wake-up. The active update groups remain in effect after the checkpoint.
``Paused`` uses the same one-second polling interval as the other status
Variables; these explicit updates do not depend on polling.

Subclasses can also call ``pausePoint()`` from an overridden ``_process()``.
Process coordinates lifecycle and pause state with a ``threading.Condition``
using its plain ``threading.Lock`` at ``_lock``. Subclasses must not replace
that lock or hold it while calling commands or ``pausePoint()``.

Design Guidance
===============

Good ``Process`` implementations usually:

* Update ``Message`` with short operator-facing status text
* Prefer ``setProgress()`` for fractional progress and ``setTotalSteps()``,
  ``setStep()``, or ``incrementSteps()`` for step-based progress
* Add explicit input or result Variables when the procedure needs operator
  parameters or produces structured output
* Check the stop condition when the work can be interrupted cleanly
* Rely on the base-class ``updateGroup`` context that wraps every ``_process()``
  call; tune its leak period via the hidden ``UpdatePeriod`` Variable rather
  than opening a redundant nested context

Related Topics
==============

* Repeating run loops and run-state control: :doc:`run_control`
* Command behavior: :doc:`/pyrogue_tree/core/command`
* Device composition and lifecycle: :doc:`/pyrogue_tree/core/device`
* Lower-level transport, protocol, and utility families: :doc:`/built_in_modules/index`

API Reference
=============

See :doc:`/api/python/pyrogue/process` for generated API details.
