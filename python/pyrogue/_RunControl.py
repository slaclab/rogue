#-----------------------------------------------------------------------------
# Company    : SLAC National Accelerator Laboratory
#-----------------------------------------------------------------------------
#  Description:
#       PyRogue base module - Run Control Device Class
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


class RunControl(pr.Device):
    """Base class for software-driven run control.

    Parameters
    ----------
    hidden : bool, optional (default = True)
        Hide the device in the tree by default.
    rates : dict, optional
        Mapping of rate enum values to display labels.
    states : dict, optional
        Mapping of state enum values to display labels.
    cmd : callable, optional
        Optional callable invoked on each run loop iteration.
    **kwargs : Any
        Additional arguments forwarded to ``pyrogue.Device``.
    """

    def __init__(
        self,
        *,
        hidden: bool = True,
        rates: dict[int, str] | None = None,
        states: dict[int, str] | None = None,
        cmd: Callable[[], None] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the run-control device."""

        if rates is None:
            rates={1:'1 Hz', 10:'10 Hz'}

        if states is None:
            states={0:'Stopped', 1:'Running'}

        pr.Device.__init__(self, hidden=hidden, **kwargs)

        value = [k for k,v in states.items()][0]

        self._thread = None
        self._threadLock = threading.Lock()
        self._cmd = cmd

        self.add(pr.LocalVariable(
            name='runState',
            value=value,
            mode='RW',
            groups=['NoConfig'],
            disp=states,
            localSet=self._setRunState,
            description='Run state of the system.'))

        value = [k for k,v in rates.items()][0]

        self.add(pr.LocalVariable(
            name='runRate',
            value=value,
            mode='RW',
            disp=rates,
            localSet=self._setRunRate,
            description='Run rate of the system.'))

        self.add(pr.LocalVariable(
            name='runCount',
            value=0,
            typeStr='UInt32',
            mode='RO',
            pollInterval=1,
            description='Run Counter updated by run thread.'))

    def _setRunState(self, value: int, changed: bool) -> None:
        """Handle run state changes.

        Sub-classes may override this method to integrate with
        external run-control hardware or software.
        """
        if not changed:
            return

        if self.runState.valueDisp() == 'Running':
            thread = None
            with self._threadLock:
                # Only create a worker when there is no active run thread.
                # This guards against repeated writes of "Running" and against
                # a stop/start sequence issued from inside the worker itself
                # before the old thread has actually exited.
                if self._thread is None or not self._thread.is_alive():
                    thread = threading.Thread(target=self._run)
                    self._thread = thread

            if thread is not None:
                # Start outside the lock so thread startup does not block other
                # state transitions. The stored self._thread reference remains
                # the ownership marker until _run() reaches its cleanup block.
                thread.start()

        else:
            with self._threadLock:
                thread = self._thread

            # When a caller outside the worker requests "Stopped", wait for the
            # current run thread to exit before returning so the state change is
            # complete from the caller's perspective.
            #
            # The current_thread() check is required because _cmd() may stop
            # the run by writing runState from inside the worker itself. A
            # thread cannot join itself, so in that case we just let _run()
            # fall out of its loop and perform the final cleanup.
            if thread is not None and threading.current_thread() is not thread:
                thread.join()

    def _setRunRate(self, value: int) -> None:
        """Set run rate.

        Override in subclasses if additional behavior is required.
        """
        pass

    def _run(self) -> None:
        """Run loop executed in a background thread."""
        #print("Thread start")
        self.runCount.set(0)

        try:
            with self.root.updateGroup(period=1.0):

                while (self.runState.valueDisp() == 'Running'):
                    time.sleep(1.0 / float(self.runRate.value()))
                    if self._cmd is not None:
                        self._cmd()

                    with self.runCount.lock:
                        self.runCount.set(self.runCount.value() + 1)
        finally:
            with self._threadLock:
                # Only the worker that currently owns self._thread is allowed
                # to clear it. This avoids a race where a stop issued from
                # inside the worker would otherwise clear the reference too
                # early and allow a second worker to start before this one has
                # fully exited.
                if self._thread is threading.current_thread():
                    self._thread = None
