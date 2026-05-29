.. _pyrogue_tree_builtin_devices_long_running_ops:

=======================
Long-running Operations
=======================

.. versionadded:: 6.14.0

Overview
========

If your :py:class:`~pyrogue.LocalCommand` runs longer than a few seconds, a
synchronous ``exec`` call ties the ZMQ client thread up until the function
returns.  For :py:class:`~pyrogue.interfaces.SimpleClient` the calling thread
blocks on ``recv`` for the entire duration.  For
:py:class:`~pyrogue.interfaces.VirtualClient` the ``linkTimeout`` is an *idle*
timeout: ``_checkLinkState`` tolerates a single in-flight request and only
declares the link stalled if the optional ``requestStallTimeout`` is set and
exceeded.  Either way the right answer is not to enlarge a timeout — it is to
choose the right dispatch pattern so the long work runs on the server while
the client thread stays responsive.  PyRogue offers two canonical approaches:
:py:class:`~pyrogue.Process` for stateful procedures that benefit from
GUI-visible progress, and ``cmd(blocking=False)`` for ad-hoc fire-and-poll
dispatch where a simple pass/fail result is enough.

Both patterns run the work on a background thread and return immediately to the
caller.  The difference is in what the tree exposes while the work is running.
Choose :py:class:`~pyrogue.Process` when the operation is multi-step and you
want built-in ``Running`` / ``Progress`` / ``Message`` status Variables that
GUI clients and scripts can poll.  Choose ``cmd(blocking=False)`` when
you need the simplest possible mechanism: fire the command, get ``None`` back
immediately, and poll the ``running`` property until the work finishes.

Comparison
==========

.. list-table::
   :header-rows: 1
   :widths: 24 38 38

   * - Attribute
     - ``pr.Process``
     - ``cmd(blocking=False)``
   * - Use case
     - Stateful multi-step procedure with GUI-visible progress and status text
     - Ad-hoc one-shot command; caller polls for completion via exposed properties
   * - State held across calls
     - Yes — ``Progress``, ``Step``, ``TotalSteps``, ``Message`` persist on the
       ``Device`` between invocations
     - Minimal — ``running``, ``result``, and ``error`` are properties on the
       Command itself; no sibling variables are added to the tree
   * - Progress / step UI
     - Built in: ``Progress`` (fraction), ``Step`` / ``TotalSteps`` (count-based),
       ``Message`` (free text); GUI widgets consume these automatically
     - Not built in; progress must flow through separate tree Variables if needed
   * - Cancel primitive
     - Built-in ``Stop`` command; procedure checks ``self._runEn``
     - None — no ``Stop`` equivalent for non-blocking Commands
   * - Status exposed
     - ``Running``, ``Progress``, ``Step``, ``TotalSteps``, ``Message``; optional
       ``argVariable`` and ``returnVariable`` as tree Variables
     - ``running`` (bool), ``result`` (last return value),
       ``error`` (last exception string, empty on success) as properties on the
       Command node
   * - Best when
     - The operation is long-running, multi-step, needs operator-visible status,
       or must be cancellable via ``Stop``
     - The operation may outlast ``linkTimeout`` and only a pass/fail result or
       simple return value is needed; existing function requires no refactoring

Pattern 1: pr.Process
=====================

Use :py:class:`~pyrogue.Process` when the procedure is naturally stateful —
calibration runs, capture workflows, multi-step initialization — and you want
``Running``, ``Progress``, and ``Message`` automatically exposed in the device
tree.  A minimal sketch:

.. code-block:: python

   import pyrogue as pr

   class ApplyCalibration(pr.Process):
       def __init__(self, **kwargs):
           super().__init__(description='Run calibration', **kwargs)

       def _process(self):
           self.setTotalSteps(3)
           for i, step in enumerate(['reset', 'load', 'verify'], 1):
               self.Message.setDisp(f'Step: {step}')
               # ... real work here ...
               self.setStep(i)

For the full ``CaptureProcess`` example with operator-facing input and result
Variables, see :doc:`process`.

Pattern 2: Command(blocking=False)
===================================

Any :py:class:`~pyrogue.LocalCommand` can be called with ``blocking=False``
to enable fire-and-poll dispatch.  No special construction-time flags are
needed — whether to block is a call-site decision:

.. code-block:: python

   import pyrogue as pr
   import time

   def _apply_config(cmd):
       steps = [('reset_defaults', 0.3), ('load_cal_table', 0.3), ('verify', 0.3)]
       for step, duration in steps:
           cmd._log.info('Config step: %s', step)
           time.sleep(duration)
       return 'configured'

   class ConfigDevice(pr.Device):
       def __init__(self, **kwargs):
           super().__init__(**kwargs)
           self.add(pr.LocalCommand(
               name='ApplyConfig',
               description='Apply full device configuration.',
               function=_apply_config,
               retValue='',
           ))

Calling ``cmd(blocking=False)`` returns ``None`` immediately because the
server dispatches a worker thread and replies before the function finishes.
Poll the command's ``running`` property on the client side to detect
completion — see the next section.

Client-Side Polling Pattern
============================

After calling with ``blocking=False``, poll the command's ``running``
property until it becomes ``False``, then read ``result`` and ``error``.
These are ``@pr.expose``-d properties on the Command itself, accessible
as direct property access through :py:class:`~pyrogue.interfaces.VirtualClient`.

The example below is the canonical reference shape for the polling loop:

.. literalinclude:: ../../../../python/pyrogue/examples/_NonBlockingCommandExample.py
   :language: python
   :pyobject: main
   :caption: VirtualClient polling loop

Interaction with linkTimeout and requestStallTimeout
=====================================================

A non-blocking call returns immediately once the server has dispatched
the worker thread — before the function body runs.  Because the reply travels
over the wire before any long-running work begins, neither ``linkTimeout`` nor
``requestStallTimeout`` fires for the dispatch call itself.

The only RPCs that race a timeout after dispatch are the subsequent
property reads of ``running``, ``result``, and ``error``.  Those are
lightweight attribute lookups and complete in well under a millisecond on
any non-pathological connection, so they are not a practical timeout concern.

Related Topics
==============

* Process-based long-running operations with progress UI: :doc:`process`
* Command behavior and dispatch semantics: :doc:`/pyrogue_tree/core/command`
* Python-defined commands: :doc:`/pyrogue_tree/core/local_command`
* Mirrored-tree remote client with ``linkTimeout`` and ``requestStallTimeout``: :doc:`/pyrogue_tree/client_interfaces/virtual`
* Lightweight string-path client (``SimpleClient``): :doc:`/pyrogue_tree/client_interfaces/simple`

API Reference
=============

See :doc:`/api/python/pyrogue/basecommand` for generated API details.
