#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
#  Description:
#       PyRogue base module - Process Device Class
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the rogue software platform, including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
from __future__ import annotations

import threading
import time
from typing import Any, Callable

import pyrogue as pr

class Process(pr.Device):
    """Special Device base class to execute complex or long running processes or algorythms involving Variables.

    Parameters
    ----------
    argVariable : object, optional
        Variable providing input arguments.
    returnVariable : object, optional
        Variable receiving return values.
    function : callable, optional
        Process callback. The wrapper provides keyword arguments
        ``root``, ``dev``, and ``arg``; the function may accept any subset
        of these names.
        Progress may be updated either as a direct fractional value with
        :meth:`setProgress`, or as a step-based ratio using
        :meth:`setTotalSteps`, :meth:`setStep`, and :meth:`incrementSteps`.
    **kwargs : Any
        Additional arguments forwarded to ``Device``.
    """

    def __init__(
        self,
        *,
        argVariable: pr.BaseVariable | None = None,
        returnVariable: pr.BaseVariable | None = None,
        function: Callable[..., Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize a process device."""

        pr.Device.__init__(self, **kwargs)

        self._lock   = threading.Lock()
        self._thread = None
        self._runEn  = False
        self._argVar = argVariable
        self._retVar = returnVariable
        self._function = function

        self._functionWrap = pr.functionWrapper(function=self._function, callArgs=['root', 'dev', 'arg'])

        self.add(pr.LocalCommand(
            name='Start',
            function=self._startProcess,
            description='Start process. No Args.'))

        self.add(pr.LocalCommand(
            name='Stop',
            function=self._stopProcess,
            description='Stop process. No Args.'))

        self.add(pr.LocalVariable(
            name='Running',
            mode='RO',
            value=False,
            pollInterval=1.0,
            description='Status values indicating if operation is running.'))

        self.add(pr.LocalVariable(
            name='Progress',
            mode='RO',
            units='Pct',
            value=0.0,
            disp = '{:1.2f}',
            localSet=self._clampProgressValue,
            pollInterval=1.0,
            description='Percent complete: 0 - 100 %.'))

        self.add(pr.LocalVariable(
            name='Message',
            mode='RO',
            value='',
            pollInterval=1.0,
            description="Process status message. Prefixed with 'Error:' if an error occurred."))

        self.add(pr.LocalVariable(
            name = 'Step',
            mode = 'RO',
            pollInterval=1.0,
            value = 1,
            localSet=self._updateProgress,
            description = "Current number of completed steps. Prefer setStep() or incrementSteps()."))

        self.add(pr.LocalVariable(
            name = 'TotalSteps',
            mode = 'RO',
            pollInterval=1.0,
            value = 1,
            localSet=self._updateProgress,
            description = "Total number of process steps. Prefer setTotalSteps()."))

        # Add arg variable if not already added
        if self._argVar is not None and self._argVar not in self:
            self.add(self._argVar)

        # Add return variable if not already added
        if self._retVar is not None and self._retVar not in self:
            self.add(self._retVar)

    @staticmethod
    def _clampedProgress(value: Any) -> float:
        """Return ``value`` clamped into the valid progress range."""
        return max(0.0, min(float(value), 1.0))

    def _clampProgressValue(
        self,
        *,
        var: pr.BaseVariable | None = None,
        value: Any,
        **kwargs: Any,
    ) -> None:
        """Clamp direct Progress writes while preserving the variable metadata range."""
        if var is not None and hasattr(var, "_block"):
            var._block._value = self._clampedProgress(value)

    def _updateProgress(self) -> None:
        """Recompute progress from ``Step`` and ``TotalSteps``.

        The step counter may temporarily run ahead of the declared total, or
        the total may still be zero while a process is being configured.
        Keep ``Progress`` bounded so helper callers cannot trip the variable
        range checks just by updating ``Step`` and ``TotalSteps`` out of order.
        """
        total = self.TotalSteps.value()

        if total <= 0:
            progress = 0.0
        else:
            progress = self.Step.value() / total

        self.setProgress(progress)

    def setProgress(self, value: float) -> None:
        """Set fractional progress directly.

        Parameters
        ----------
        value : float
            Fractional completion value. Values outside the valid ``0.0`` to
            ``1.0`` range are clamped before being stored in ``Progress``.
        """
        self.Progress.set(self._clampedProgress(value))

    def setTotalSteps(self, value: int) -> None:
        """Set the total number of steps used for step-based progress.

        Parameters
        ----------
        value : int
            Total number of expected steps. Non-positive totals cause the
            derived progress ratio to read back as ``0.0``.
        """
        self.TotalSteps.set(value)

    def setStep(self, value: int) -> None:
        """Set the absolute completed-step count and refresh progress.

        Parameters
        ----------
        value : int
            Absolute completed-step count used when deriving progress from
            ``Step`` and ``TotalSteps``.
        """
        self.Step.set(value)

    def incrementSteps(self, incr: int = 1) -> None:
        """Advance the completed-step count and refresh progress.

        Parameters
        ----------
        incr : int, optional
            Number of completed steps to add. The updated progress ratio is
            recomputed from ``Step`` and ``TotalSteps`` and clamped into the
            valid ``0.0`` to ``1.0`` range.
        """
        with self.Step.lock:
            self.Step.set(self.Step.value() + incr)

    def _incrementSteps(self, incr: int) -> None:
        """Increment step counter and update progress.

        Parameters
        ----------
        incr : int
            Number of steps to add.

        Notes
        -----
        Compatibility wrapper for existing code. Prefer
        :meth:`incrementSteps` in new code.
        """
        self.incrementSteps(incr)

    def _setSteps(self, value: int) -> None:
        """Set absolute step counter and update progress.

        Parameters
        ----------
        value : int
            New step index.

        Notes
        -----
        Compatibility wrapper for existing code. Prefer :meth:`setStep` in
        new code.
        """
        self.setStep(value)

    def _startProcess(self) -> None:
        """ """
        with self._lock:
            if self.Running.value() is False:
                self._runEn  = True
                self._thread = threading.Thread(target=self._run)
                self._thread.start()
            else:
                self._log.warning("Process already running!")

    def _stopProcess(self) -> None:
        """Signal the worker to stop and wait for it to exit."""
        with self._lock:
            self._runEn  = False
            thr = self._thread

        # Self-thread guard: _run() can land here via setDisp('Stopped').
        if (thr is not None
                and hasattr(thr, 'is_alive') and thr.is_alive()
                and hasattr(thr, 'join')
                and threading.current_thread() is not thr):
            thr.join()

    def _stop(self) -> None:
        """ """
        self._stopProcess()
        pr.Device._stop(self)

    def __call__(self, arg: Any = None) -> None:
        """Start the process with an optional argument.

        Parameters
        ----------
        arg : object, optional
            Argument to set on ``argVariable`` before running.
        """
        with self._lock:
            if self.Running.value() is False:
                if arg is not None and self._argVar is not None:
                    self._argVar.setDisp(arg)

                self._runEn  = True
                self._thread = threading.Thread(target=self._run)
                self._thread.start()
            else:
                self._log.warning("Process already running!")

        return None

    def _run(self) -> None:
        """ """
        self.Running.set(True)

        try:
            with self.root.updateGroup(period=1.0):
                self._process()
        except Exception as e:
            pr.logException(self._log,e)
            self.Message.setDisp("Stopped after error!")

        self.Running.set(False)

    def _process(self) -> None:
        """ """

        # User has provided a function Update status at start and end and call their function
        if self._function is not None:
            self.Message.setDisp("Running")
            self.setStep(0)
            self.setProgress(0.0)

            if self._argVar is not None:
                arg = self._argVar.get()
            else:
                arg = None

            ret = self._functionWrap(function=self._function, root=self.root, dev=self, arg=arg)

            if self._retVar is not None:
                self._retVar.set(ret)

            self.Message.setDisp("Done")
            self.setProgress(1.0)

        # No function run example process
        else:
            self.Message.setDisp("Started")
            self.setStep(0)
            self.setTotalSteps(100)
            for i in range(100):
                if self._runEn is False:
                    break
                time.sleep(1)
                self.setStep(i+1)
                self.Message.setDisp(f"Running for {i} seconds.")
            self.Message.setDisp("Done")
