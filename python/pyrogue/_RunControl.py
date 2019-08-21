#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Title      : PyRogue base module - Run Control Device Class
#-----------------------------------------------------------------------------
# File       : pyrogue/_RunControl.py
# Created    : 2019-08-06
#-----------------------------------------------------------------------------
# This file is part of the rogue software platform. It is subject to 
# the license terms in the LICENSE.txt file found in the top-level directory 
# of this distribution and at: 
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html. 
# No part of the rogue software platform, including this file, may be 
# copied, modified, propagated, or distributed except according to the terms 
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------
import rogue.interfaces.memory as rim
import collections
import datetime
import functools as ft
import pyrogue as pr
import inspect
import threading
import math
import time

class RunControl(pr.Device):
    """Special base class to control runs. """

    def __init__(self, *, visibility=0, rates=None, states=None, cmd=None, **kwargs):
        """Initialize device class"""

        if rates is None:
            rates={1:'1 Hz', 10:'10 Hz'}

        if states is None:
            states={0:'Stopped', 1:'Running'}

        pr.Device.__init__(self, visibility=visibility, **kwargs)

        value = [k for k,v in states.items()][0]

        self._thread = None
        self._cmd = cmd

        self.add(pr.LocalVariable(
            name='runState',
            value=value,
            mode='RW',
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
        """
        Set run state. Reimplement in sub-class.
        Enum of run states can also be overriden.
        Underlying run control must update runCount variable.
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
        """
        Set run rate. Reimplement in sub-class if neccessary.
        """
        pass

    def _run(self):
        #print("Thread start")
        self.runCount.set(0)

        while (self.runState.valueDisp() == 'Running'):
            time.sleep(1.0 / float(self.runRate.value()))
            if self._cmd is not None:
                self._cmd()

            self.runCount.set(self.runCount.value() + 1,write=False)
        #print("Thread stop")

