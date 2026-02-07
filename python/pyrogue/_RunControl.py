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
import threading
import time
from typing import Any, Callable, Optional

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
        rates: Optional[dict[int, str]] = None,
        states: Optional[dict[int, str]] = None,
        cmd: Optional[Callable[[], None]] = None,
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
        if changed:
            if self.runState.valueDisp() == 'Running':
                #print("Starting run")
                self._thread = threading.Thread(target=self._run)
                self._thread.start()
            elif self._thread is not None:
                #print("Stopping run")
                self._thread.join()
                self._thread = None

    def _setRunRate(self, value: int) -> None:
        """Set run rate.

        Override in subclasses if additional behavior is required.
        """
        pass

    def _run(self) -> None:
        """Run loop executed in a background thread."""
        #print("Thread start")
        self.runCount.set(0)

        with self.root.updateGroup(period=1.0):

            while (self.runState.valueDisp() == 'Running'):
                time.sleep(1.0 / float(self.runRate.value()))
                if self._cmd is not None:
                    self._cmd()

                with self.runCount.lock:
                    self.runCount.set(self.runCount.value() + 1)
