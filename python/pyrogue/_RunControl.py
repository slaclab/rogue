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
import pyrogue as pr
import threading
import time

from collections.abc import Callable
from typing import Dict, Optional, Union, Type

class RunControl(pr.Device):
    """Special base class to control runs.

    Args:
        hidden: Whether the device is visible to external classes.
        rates: A dictionary of rates and associated keys. The keys are application specific and
            represent the run rate in hz in the default class.
        states: A dictionary of states and associated keys. The keys are application specific
        cmd: Is the command to execute at each iteration when using the default software driven run() method.
        **kwargs:
    """

    def __init__(self, *,
                 hidden: bool = True,
                 rates: Optional[Dict] = {1:'1 Hz', 10:'10 Hz'},
                 states: Optional[Dict] = {0:'Stopped', 1:'Running'},
                 cmd: Optional[Union[Callable, Type['pr.Command'] ]] = None,
                 **kwargs):

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

    def _setRunState(self,value,changed):
        """Set run state. Creates a run thread when started, or kills/deletes a run thread when stopped.
        Re-implement in sub-class. Enum of run states can also be overridden.
        Underlying run control must update runCount variable.
        A custom run control class may issue writes to hardware to set the run state.

        Args:
            value:
            changed:

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

    def _setRunRate(self,value):
        """Set run rate. Called when runRate variable is set.
        Re-implement in sub-class if necessary.
        A custom run control class may issue a write to hardware to adjust the run rate.

        Args:
            value:

        """
        pass

    def _run(self):
        """Background method used by the run thread when using the default runState method.
        A custom run control class may modify this method or not use it if setRunState does not start a thread.
        """
        #print("Thread start")
        self.runCount.set(0)

        with self.root.updateGroup(period=1.0):

            while (self.runState.valueDisp() == 'Running'):
                time.sleep(1.0 / float(self.runRate.value()))
                if self._cmd is not None:
                    self._cmd()

                with self.runCount.lock:
                    self.runCount.set(self.runCount.value() + 1)
